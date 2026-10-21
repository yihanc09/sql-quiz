"""API contract tests without external accounts or database writes."""
import io
import json
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

import sql_quiz.web as web
@pytest.fixture
def api_request(monkeypatch):
    monkeypatch.setattr(web, "SESSIONS", {})
    client = Mock()
    client.auth.get_user.return_value.user = SimpleNamespace(id="student", email="student@example.com")
    web.SESSIONS["test"] = {"client": client, "expires": time.time() + 60, "lock": threading.Lock()}
    monkeypatch.setattr(web, "load_answer_records", Mock(return_value={}))
    monkeypatch.setattr(web, "record_query_event", Mock())
    monkeypatch.setattr(web, "save_answer", Mock())
    monkeypatch.setattr(web, "save_graded_answer", Mock())

    def send(path, data=None, authenticated=True, origin="http://localhost:8000"):
        handler = web.Handler.__new__(web.Handler)
        body = json.dumps(data or {}).encode()
        handler.path = path
        handler.headers = {"Content-Type": "application/json", "Content-Length": str(len(body)),
                           "Host": "localhost:8000", "Origin": origin,
                           "Cookie": "quiz_session=test" if authenticated else ""}
        handler.rfile = io.BytesIO(body)
        handler.reply = Mock()
        if data is None:
            handler.do_GET()
        else:
            handler.do_POST()
        return handler.reply.call_args.args
    return send


def test_questions_do_not_expose_reference_sql(api_request):
    status, payload = api_request("/api/questions")
    assert status == 200 and len(payload["questions"]) == 5
    assert all("expected_sql" not in q for q in payload["questions"])


@pytest.mark.parametrize("action", ["run", "save", "submit"])
def test_authentication_required(api_request, action):
    assert api_request(f"/api/{action}", {"question_id": 1, "sql": "SELECT 1"}, False)[0] == 401


def test_cross_origin_rejected(api_request):
    assert api_request("/api/run", {"sql": "SELECT 1"}, origin="https://example.com")[0] == 403


@pytest.mark.parametrize("sql", ["DELETE FROM public.artist", "SELECT 1; SELECT 2"])
def test_unsafe_statements_rejected(api_request, monkeypatch, sql):
    execute = Mock()
    monkeypatch.setattr(web, "run_query", execute)
    assert api_request("/api/run", {"question_id": 1, "sql": sql})[0] == 400
    execute.assert_not_called()


def test_submission_grades_and_persists(api_request, monkeypatch):
    monkeypatch.setattr(web, "run_query", Mock(return_value=pd.DataFrame({"total_artists": [275]})))
    status, payload = api_request("/api/submit", {"question_id": 1, "sql": "SELECT COUNT(*) AS total_artists FROM public.artist"})
    assert status == 200 and payload["grade"]["score"] == 4
    assert payload["table"]["data"] == [[275]]
    web.save_graded_answer.assert_called_once()
    assert web.record_query_event.call_args.args[2:4] == ("SUBMIT_QUERY", True)
    assert web.record_query_event.call_args.args[4] == "SELECT COUNT(*) AS total_artists FROM public.artist"


def test_save_preserves_unchanged_grade(api_request):
    web.load_answer_records.return_value = {1: {"sql_answer": "SELECT 1", "score": 4}}
    assert api_request("/api/save", {"question_id": 1, "sql": "SELECT 1"})[0] == 200
    web.save_answer.assert_not_called()


def test_save_changed_answer_clears_grade(api_request):
    web.load_answer_records.return_value = {1: {"sql_answer": "SELECT 1", "score": 4}}
    assert api_request("/api/save", {"question_id": 1, "sql": "SELECT 2"})[0] == 200
    web.save_answer.assert_called_once()


def test_failed_execution_audited(api_request, monkeypatch):
    monkeypatch.setattr(web, "run_query", Mock(side_effect=RuntimeError("private connection information")))
    status, payload = api_request("/api/run", {"question_id": 1, "sql": "SELECT 1"})
    assert status == 400 and "private connection" not in payload["error"]
    assert web.record_query_event.call_args.args[2:4] == ("RUN_QUERY", False)
    assert web.record_query_event.call_args.args[4] == "SELECT 1"


def test_logout_clears_local_session(api_request):
    status, _, cookie = api_request("/api/logout", {})
    assert status == 200 and "Max-Age=0" in cookie
    assert not web.SESSIONS


def test_missing_private_configuration_is_not_reported_as_invalid_login(api_request, monkeypatch):
    message = "Run python -m scripts.configure_runtime --init once to initialize private settings."
    monkeypatch.setattr(web, "sign_in", Mock(side_effect=web.RuntimeConfigError(message)))
    status, payload = api_request("/api/login", {"email": "student@example.com", "password": "test"}, False)
    assert status == 503
    assert payload["error"] == message


def test_hint_requires_authentication(api_request, monkeypatch):
    execute = Mock()
    monkeypatch.setattr(web, 'run_query', execute)
    assert api_request('/api/hint', {'question_id': 1}, False)[0] == 401
    execute.assert_not_called()


def test_hint_executes_reference_again_each_time(api_request, monkeypatch):
    execute = Mock(side_effect=[pd.DataFrame({'total_artists': [275]}),
                                pd.DataFrame({'total_artists': [276]})])
    monkeypatch.setattr(web, 'run_query', execute)
    first = api_request('/api/hint', {'question_id': 1})
    second = api_request('/api/hint', {'question_id': 1})
    assert first[1]['rows'] == [[275]]
    assert second[1]['rows'] == [[276]]
    assert second[1]['source'] == 'live_database'
    assert 'public.artist' in second[1]['expected_sql']
    assert execute.call_count == 2


@pytest.mark.parametrize('qid', [True, 0, 6, '1', None])
def test_invalid_hint_question_rejected(api_request, monkeypatch, qid):
    execute = Mock()
    monkeypatch.setattr(web, 'run_query', execute)
    assert api_request('/api/hint', {'question_id': qid})[0] == 400
    execute.assert_not_called()


def test_hint_database_failure_has_no_static_fallback(api_request, monkeypatch):
    monkeypatch.setattr(web, 'run_query', Mock(side_effect=RuntimeError('private password')))
    status, payload = api_request('/api/hint', {'question_id': 1})
    assert status == 502
    assert 'rows' not in payload
    assert 'private password' not in payload['error']


def test_grading_uses_current_database_instead_of_snapshot(api_request, monkeypatch):
    # The committed snapshot says 275; the live database now says 276.
    execute = Mock(return_value=pd.DataFrame({'total_artists': [276]}))
    monkeypatch.setattr(web, 'run_query', execute)
    status, payload = api_request('/api/submit', {'question_id': 1, 'sql': 'SELECT 276 AS total_artists'})
    assert status == 200 and payload['grade']['score'] == 4
    assert execute.call_args_list[0].args == ('SELECT 276 AS total_artists',)
    assert 'public.artist' in execute.call_args_list[1].args[0]


def test_reference_failure_does_not_save_grade(api_request, monkeypatch):
    monkeypatch.setattr(web, 'run_query', Mock(side_effect=[
        pd.DataFrame({'total_artists': [275]}), RuntimeError('secret DB address')]))
    status, payload = api_request('/api/submit', {'question_id': 1, 'sql': 'SELECT 275 AS total_artists'})
    assert status == 502 and 'grade' not in payload
    assert payload['table']['data'] == [[275]]
    assert 'secret DB address' not in payload['error']
    web.save_graded_answer.assert_not_called()


def test_all_uploaded_tables_and_shared_hints_are_in_metadata(api_request):
    status, payload = api_request('/api/questions')
    assert status == 200
    assert payload['database']['schema'] == 'public'
    assert len(payload['database']['tables']) == 11
    assert all(q['hint']['connections'] and q['tables'] for q in payload['questions'])


def test_valid_login_survives_unavailable_submission_storage(api_request, monkeypatch):
    user = SimpleNamespace(id='student', email='student@example.com')
    session = SimpleNamespace(access_token='access', refresh_token='refresh')
    client = web.SESSIONS['test']['client']
    monkeypatch.setattr(web, 'sign_in', Mock(return_value=SimpleNamespace(user=user, session=session)))
    monkeypatch.setattr(web, 'get_supabase_client', Mock(return_value=client))
    web.load_answer_records.side_effect = RuntimeError('PGRST205 private database details')
    status, payload, cookie = api_request('/api/login', {'email': user.email, 'password': 'test'}, False)
    assert status == 200 and payload['user']['email'] == user.email
    assert payload['records'] == {} and 'warning' in payload
    assert 'private database' not in payload['warning']
    assert 'quiz_session=' in cookie


def test_session_verification_survives_unavailable_submission_storage(api_request):
    web.load_answer_records.side_effect = RuntimeError('Storage unavailable')
    status, payload = api_request('/api/session')
    assert status == 200 and payload['user']['email'] == 'student@example.com'
    assert payload['records'] == {} and 'warning' in payload


def test_storage_outage_does_not_block_authenticated_query(api_request, monkeypatch):
    web.load_answer_records.side_effect = RuntimeError('Storage unavailable')
    monkeypatch.setattr(web, 'run_query', Mock(return_value=pd.DataFrame({'n': [1]})))
    status, payload = api_request('/api/run', {'question_id': 1, 'sql': 'SELECT 1 AS n'})
    assert status == 200 and payload['table']['data'] == [[1]]


def test_invalid_credentials_do_not_create_session(api_request, monkeypatch):
    monkeypatch.setattr(web, 'sign_in', Mock(side_effect=RuntimeError('invalid credentials')))
    original = set(web.SESSIONS)
    result = api_request('/api/login', {'email': 'student@example.com', 'password': 'wrong'}, False)
    assert result[0] == 400 and len(result) == 2
    assert set(web.SESSIONS) == original
