"""Initialize/check private settings without printing their values.

Run --init once from the existing configured local checkout, then deploy with
only DATABASE_URL and DATABASE_PASSWORD. Existing settings are never overwritten.
"""

import argparse
import os
from pathlib import Path

import psycopg
from cryptography.fernet import Fernet
from dotenv import dotenv_values
from psycopg.types.json import Jsonb

from runtime_config import PRIVATE_SETTINGS, RuntimeConfigError, backend_connection


def seed_settings(conn, source=None):
    existing = conn.execute(
        "SELECT settings FROM quiz_private.runtime_config WHERE singleton = %s", (True,)
    ).fetchone()
    if existing:
        missing = [name for name in PRIVATE_SETTINGS if not existing[0].get(name)]
        if missing:
            raise RuntimeConfigError("Existing private settings are incomplete; review them with the database administrator.")
        return False
    source = os.environ if source is None else source
    values = {name: source.get(name, "") for name in PRIVATE_SETTINGS}
    missing = [name for name in PRIVATE_SETTINGS if name != "APP_SESSION_KEY" and not values[name]]
    if missing:
        raise RuntimeConfigError(
            "First-time initialization must run from the original configured local checkout. "
            "Missing local settings: " + ", ".join(missing)
        )
    if not values["APP_SESSION_KEY"]:
        values["APP_SESSION_KEY"] = Fernet.generate_key().decode()
    Fernet(values["APP_SESSION_KEY"].encode("ascii"))
    conn.execute(
        "INSERT INTO quiz_private.runtime_config (singleton, settings) VALUES (%s, %s) "
        "ON CONFLICT (singleton) DO NOTHING",
        (True, Jsonb(values)),
    )
    return True


def check_private_permissions(conn):
    checks = []
    for role in ("quiz_reader", "authenticated", "anon"):
        for privilege in ("USAGE", "CREATE"):
            allowed = conn.execute(
                "SELECT has_schema_privilege(%s, %s, %s)", (role, "quiz_private", privilege)
            ).fetchone()[0]
            checks.append((f"{role}: no private-schema {privilege}", not allowed))
        for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"):
            allowed = conn.execute(
                "SELECT has_table_privilege(%s, %s, %s)",
                (role, "quiz_private.runtime_config", privilege),
            ).fetchone()[0]
            checks.append((f"{role}: no private-config {privilege}", not allowed))
    enabled = conn.execute(
        "SELECT relrowsecurity FROM pg_class WHERE oid = %s::regclass", ("quiz_private.runtime_config",)
    ).fetchone()[0]
    checks.append(("Private configuration has RLS enabled", enabled))
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--init", action="store_true", help="Apply private-schema migration and seed existing local settings")
    group.add_argument("--check", action="store_true", help="Verify student-facing roles cannot access private settings")
    parser.add_argument("--from-env", type=Path, help="Read initial private settings from a local backup without replacing the two deployment variables")
    args = parser.parse_args()
    if args.from_env and (not args.init or not args.from_env.is_file()):
        parser.error("--from-env requires --init and an existing local file")
    try:
        with backend_connection() as conn:
            if args.init:
                conn.autocommit = True
                migration = Path(__file__).resolve().parent / "sql" / "002_runtime_configuration.sql"
                conn.execute(migration.read_text(), prepare=False)
                with conn.transaction():
                    source = dotenv_values(args.from_env) if args.from_env else None
                    created = seed_settings(conn, source)
                print("Private settings initialized." if created else "Existing private settings retained.")
            checks = check_private_permissions(conn)
            for label, passed in checks:
                print(f"{'PASS' if passed else 'FAIL'} {label}")
            if not all(passed for _, passed in checks):
                raise SystemExit(1)
    except (psycopg.Error, RuntimeConfigError, ValueError):
        print("Private configuration operation failed. Check the administrator connection and existing local configuration.")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
