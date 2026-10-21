"""Load backend-only settings with just two deployment environment variables."""

import os
from functools import lru_cache

import psycopg
from dotenv import load_dotenv
from sql_quiz.paths import PROJECT_ROOT

load_dotenv(PROJECT_ROOT / ".env")

PRIVATE_SETTINGS = ("SUPABASE_URL", "SUPABASE_ANON_KEY", "QUIZ_DATABASE_URL", "APP_SESSION_KEY")


class RuntimeConfigError(ValueError):
    """An actionable configuration error without database credentials."""


def backend_connection():
    """Use the session-pool URI and bind its password as a connection option."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeConfigError("DATABASE_URL must be configured.")
    options = {"connect_timeout": 10}
    password = os.getenv("DATABASE_PASSWORD")
    if password:
        options["password"] = password
    return psycopg.connect(url, **options)


@lru_cache(maxsize=1)
def _private_settings():
    try:
        with backend_connection() as conn:
            conn.execute("SET TRANSACTION READ ONLY")
            row = conn.execute(
                "SELECT settings FROM quiz_private.runtime_config WHERE singleton = %s",
                (True,),
            ).fetchone()
    except psycopg.Error:
        raise RuntimeConfigError(
            "Cannot load private configuration. Check DATABASE_URL / DATABASE_PASSWORD "
            "and run python -m scripts.admin.configure_runtime --init once."
        ) from None
    if not row or not isinstance(row[0], dict):
        raise RuntimeConfigError("Run python -m scripts.admin.configure_runtime --init once to initialize private settings.")
    return row[0]


def get_setting(name):
    """Legacy local settings remain valid; deployed apps read the private table."""
    if name not in PRIVATE_SETTINGS:
        raise RuntimeConfigError("Unknown private configuration setting.")
    value = os.getenv(name) or _private_settings().get(name)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeConfigError("Private configuration is incomplete. Run python -m scripts.admin.configure_runtime --init.")
    return value
