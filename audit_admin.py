"""Instructor-only audit migration, integrity verification, and log inspection.

DATABASE_URL must be a trusted backend/admin connection, never quiz_reader.
"""

import argparse
import json
from pathlib import Path

import psycopg
from psycopg import sql

from database import get_connection

TABLE = "public.quiz_audit_log"
PRIVILEGES = ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER")


def check_integrity(conn, taker_role, taker_conn):
    """Check effective privileges and real denied operations, rolling back probes.

    Use a writable admin transaction: a read-only transaction could reject a
    write for the wrong reason and falsely suggest that permissions are safe.
    """
    checks = []
    for role in dict.fromkeys((taker_role, "authenticated", "anon")):
        info = conn.execute(
            "SELECT rolsuper, rolbypassrls, rolcreaterole FROM pg_roles WHERE rolname = %s",
            (role,),
        ).fetchone()
        checks.append((f"{role}: no administrative role flags", info is not None and not any(info)))
        for privilege in PRIVILEGES:
            allowed = conn.execute("SELECT has_table_privilege(%s, %s, %s)", (role, TABLE, privilege)).fetchone()[0]
            checks.append((f"{role}: no {privilege} privilege", not allowed))
        owner = conn.execute(
            "SELECT pg_has_role(%s, c.relowner, 'USAGE') FROM pg_class c WHERE c.oid = %s::regclass",
            (role, TABLE),
        ).fetchone()[0]
        checks.append((f"{role}: cannot act as audit-table owner", not owner))
        # No existing records are touched; TRUNCATE is also rolled back if an
        # unsafe grant unexpectedly permits it. Every probe has its own savepoint.
        probe = taker_conn if role == taker_role else conn
        for operation in (
            "UPDATE public.quiz_audit_log SET action = action WHERE false",
            "DELETE FROM public.quiz_audit_log WHERE false",
            "TRUNCATE public.quiz_audit_log",
        ):
            denied = False
            with probe.transaction(force_rollback=True):
                probe.execute("SET LOCAL lock_timeout = '2s'")
                if role != taker_role:
                    probe.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(role)))
                try:
                    with probe.transaction():
                        probe.execute(operation)
                except psycopg.errors.InsufficientPrivilege:
                    denied = True
            checks.append((f"{role}: actual {operation.split()[0]} denied (SQLSTATE 42501)", denied))
    row = conn.execute(
        "SELECT relrowsecurity FROM pg_class WHERE oid = %s::regclass", (TABLE,)
    ).fetchone()
    checks.append(("Audit table has RLS enabled", bool(row and row[0])))
    for table, trigger in (
        ("public.quiz_answers", "trg_quiz_answer_audit"),
        (TABLE, "trg_quiz_audit_no_edit"),
        (TABLE, "trg_quiz_audit_no_truncate"),
    ):
        enabled = conn.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid=%s::regclass "
            "AND tgname=%s AND tgenabled IN ('O','A') AND NOT tgisinternal)",
            (table, trigger),
        ).fetchone()[0]
        checks.append((f"{trigger}: enabled", enabled))
    for role in (taker_role, "authenticated", "anon"):
        for function in ("public.log_quiz_answer_change()", "public.reject_quiz_audit_mutation()"):
            allowed = conn.execute(
                "SELECT has_function_privilege(%s, %s, 'EXECUTE')", (role, function)
            ).fetchone()[0]
            checks.append((f"{role}: no direct execution of {function}", not allowed))
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--apply", action="store_true", help="Apply sql/001_audit_hardening.sql")
    group.add_argument("--check", action="store_true", help="Verify taker permissions and append-only protection")
    group.add_argument("--recent", type=int, metavar="N", help="Show up to N audit entries (1–100)")
    args = parser.parse_args()
    if args.recent is not None and not 1 <= args.recent <= 100:
        parser.error("--recent must be between 1 and 100")
    try:
        with get_connection(read_only=False) as conn:
            if args.apply:
                conn.autocommit = True
                migration = Path(__file__).resolve().parent / "sql" / "001_audit_hardening.sql"
                conn.execute(migration.read_text(), prepare=False)
                print("Audit migration applied; existing records retained.")
            elif args.check:
                with get_connection() as taker:
                    with taker.transaction(force_rollback=True):
                        taker.execute("SET TRANSACTION READ WRITE")
                        taker.execute("SET LOCAL statement_timeout = '10s'")
                        taker_role = taker.execute("SELECT current_user").fetchone()[0]
                        with conn.transaction(force_rollback=True):
                            conn.execute("SET LOCAL statement_timeout = '10s'")
                            checks = check_integrity(conn, taker_role, taker)
                for label, passed in checks:
                    print(f"{'PASS' if passed else 'FAIL'} {label}")
                if not all(passed for _, passed in checks):
                    raise SystemExit(1)
            else:
                conn.execute("SET TRANSACTION READ ONLY")
                rows = conn.execute(
                    "SELECT id, user_id, action, question_id, created_at, success, sql_answer, source "
                    "FROM public.quiz_audit_log ORDER BY created_at DESC, id DESC LIMIT %s",
                    (args.recent,),
                ).fetchall()
                names = ("id", "user_id", "action", "question_id", "created_at", "success", "sql_answer", "source")
                print(json.dumps([dict(zip(names, row)) for row in rows], default=str, indent=2))
    except psycopg.Error as exc:
        # Connection exceptions may contain hosts, user names, or DSNs.
        print(f"Database operation failed ({exc.sqlstate or type(exc).__name__}). Check backend configuration and permissions.")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
