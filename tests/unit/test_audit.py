"""Security regressions without network or database credentials."""
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

import sql_quiz.auth as auth
import sql_quiz.database as database
import scripts.admin.audit_admin as audit_admin
import psycopg


def test_run_query_keeps_parameters_separate_and_prepares_statement(monkeypatch):
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.description = [SimpleNamespace(name="value")]
    attack = "'; DELETE FROM public.quiz_audit_log; --"
    cursor.fetchmany.return_value = [(attack,)]
    monkeypatch.setattr(database, "get_connection", Mock(return_value=conn))
    conn.__enter__.return_value = conn
    result = database.run_query("SELECT %s AS value", (attack,))
    cursor.execute.assert_called_once_with("SELECT %s AS value", (attack,), prepare=True)
    conn.execute.assert_any_call("SET TRANSACTION READ ONLY")
    assert result.iloc[0]["value"] == attack


def test_query_event_binds_sql_and_derives_identity_from_verified_user(monkeypatch):
    client = Mock()
    client.auth.get_user.return_value.user = SimpleNamespace(id="verified-student")
    conn = MagicMock()
    conn.__enter__.return_value = conn
    connect = Mock(return_value=conn)
    monkeypatch.setattr(auth, "get_connection", connect)
    attack = "SELECT 'test'; DELETE FROM public.quiz_audit_log; --"
    auth.record_query_event(client, 1, "RUN_QUERY", False, attack)
    query, values = conn.execute.call_args.args
    assert attack not in query
    assert values == ("verified-student", "RUN_QUERY", 1, False, attack, "server")
    assert query.count("%s") == len(values)
    connect.assert_called_once_with(read_only=False)
    client.rpc.assert_not_called()


def test_query_event_requires_verified_user(monkeypatch):
    client = Mock()
    client.auth.get_user.return_value.user = None
    connect = Mock()
    monkeypatch.setattr(auth, "get_connection", connect)
    with pytest.raises(ValueError, match="Authentication required"):
        auth.record_query_event(client, 1, "RUN_QUERY", True, "SELECT 1")
    connect.assert_not_called()


@pytest.mark.parametrize("qid,action,success,text", [
    (True, "RUN_QUERY", True, "SELECT 1"),
    (6, "RUN_QUERY", True, "SELECT 1"),
    (1, "UPDATE_LOG", True, "SELECT 1"),
    (1, "RUN_QUERY", None, "SELECT 1"),
    (1, "RUN_QUERY", True, ""),
])
def test_invalid_query_event_never_connects(monkeypatch, qid, action, success, text):
    connect = Mock()
    monkeypatch.setattr(auth, "get_connection", connect)
    with pytest.raises(ValueError):
        auth.record_query_event(Mock(), qid, action, success, text)
    connect.assert_not_called()


def test_integrity_probe_uses_real_taker_connection():
    admin, taker = MagicMock(), MagicMock()

    def execute(query, params=None):
        if isinstance(query, str) and query.startswith(("UPDATE ", "DELETE ", "TRUNCATE ")):
            raise psycopg.errors.InsufficientPrivilege("permission denied")
        if isinstance(query, str) and "rolsuper" in query:
            row = (False, False, False)
        elif isinstance(query, str) and ("relrowsecurity" in query or "SELECT EXISTS" in query):
            row = (True,)
        else:
            row = (False,)
        return SimpleNamespace(fetchone=lambda: row)

    admin.execute.side_effect = execute
    taker.execute.side_effect = execute
    checks = audit_admin.check_integrity(admin, "quiz_reader", taker)
    assert all(passed for _, passed in checks)
    taker_statements = [call.args[0] for call in taker.execute.call_args_list]
    assert sum(s.startswith(("UPDATE ", "DELETE ", "TRUNCATE ")) for s in taker_statements) == 3
    assert not any("SET LOCAL ROLE" in str(s) for s in taker_statements)
    for call in taker.transaction.call_args_list:
        if call.kwargs:
            assert call.kwargs == {"force_rollback": True}
