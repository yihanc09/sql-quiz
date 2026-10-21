"""Integration and security checks using the restricted quiz database role."""

import pytest

from database import run_query


def test_select_query_allowed():
    """Normal SELECT queries should execute successfully."""
    result = run_query("SELECT COUNT(*) AS total_artists FROM chinook.artist")
    assert result.iloc[0]["total_artists"] == 275


def test_create_table_blocked():
    with pytest.raises(Exception):
        run_query("CREATE TABLE chinook.test_security (id INTEGER)")


def test_delete_blocked():
    with pytest.raises(Exception):
        run_query("DELETE FROM chinook.artist WHERE artist_id = 1")


def test_update_blocked():
    with pytest.raises(Exception):
        run_query("UPDATE chinook.artist SET name = 'Changed' WHERE artist_id = 1")


def test_multiple_statements_blocked():
    with pytest.raises(Exception):
        run_query("SELECT 1; DELETE FROM chinook.artist WHERE artist_id = 1")


def test_answer_table_not_readable():
    with pytest.raises(Exception):
        run_query("SELECT * FROM public.quiz_answers")


@pytest.mark.parametrize("privilege", ["SELECT", "INSERT", "UPDATE", "DELETE"])
def test_quiz_reader_has_no_audit_table_privileges(privilege):
    """Verify the actual connected quiz role has no direct audit-table privileges."""
    result = run_query(
        "SELECT has_table_privilege(current_user, 'public.quiz_audit_log', "
        "%s) AS allowed", (privilege,)
    )
    assert bool(result.iloc[0]["allowed"]) is False


@pytest.mark.parametrize("privilege", ["SELECT", "INSERT", "UPDATE", "DELETE"])
def test_authenticated_has_no_audit_table_privileges(privilege):
    """Check Supabase's authenticated role without requiring admin credentials."""
    result = run_query(
        "SELECT has_table_privilege('authenticated', 'public.quiz_audit_log', "
        "%s) AS allowed", (privilege,)
    )
    assert bool(result.iloc[0]["allowed"]) is False


def test_audit_log_not_readable_by_quiz_reader():
    """An actual attempt to read audit records must be rejected."""
    with pytest.raises(Exception):
        run_query("SELECT * FROM public.quiz_audit_log LIMIT 1")


def test_audit_trigger_is_security_definer():
    """The answer audit trigger should execute with its owner's privileges."""
    result = run_query(
        "SELECT p.prosecdef AS security_definer "
        "FROM pg_catalog.pg_proc AS p "
        "JOIN pg_catalog.pg_namespace AS n ON n.oid = p.pronamespace "
        "WHERE n.nspname = 'public' "
        "AND p.proname = 'log_quiz_answer_change' "
        "AND p.pronargs = 0"
    )
    assert len(result) == 1
    assert bool(result.iloc[0]["security_definer"]) is True


def test_audit_trigger_function_not_callable_by_quiz_reader():
    """The restricted role must not have direct EXECUTE permission."""
    result = run_query(
        "SELECT has_function_privilege(current_user, "
        "'public.log_quiz_answer_change()', 'EXECUTE') AS allowed"
    )
    assert bool(result.iloc[0]["allowed"]) is False


def test_parameter_payload_is_returned_as_data():
    attack = "'; DELETE FROM public.quiz_audit_log; --"
    result = run_query("SELECT %s::text AS value", (attack,))
    assert result.iloc[0]["value"] == attack


def test_stacked_selects_rejected_by_driver():
    # Both statements are read-only; a read-only transaction alone cannot pass this test.
    from psycopg.errors import SyntaxError
    with pytest.raises(SyntaxError):
        run_query("SELECT 1; SELECT 2")
