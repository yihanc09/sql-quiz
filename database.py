import os

import pandas as pd
import psycopg
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


def get_connection(read_only=True):
    """Connect to Supabase PostgreSQL."""

    env_name = "QUIZ_DATABASE_URL" if read_only else "DATABASE_URL"
    database_url = os.getenv(env_name)

    if not database_url:
        raise ValueError(f"{env_name} is not configured.")

    return psycopg.connect(database_url, connect_timeout=10)


def run_query(sql, params=None):
    """Execute one read-only statement, binding data values separately.

    Application-owned queries use %s placeholders and a tuple/dict of parameters.
    A student's complete SQL statement is intentionally the statement itself;
    it cannot be bound as a value. Preparation rejects stacked statements even
    for callers that do not use the web/Streamlit validation layer.
    """

    with get_connection() as conn:
        # Enforce a read-only transaction with a timeout.
        with conn.transaction():
            conn.execute("SET TRANSACTION READ ONLY")
            conn.execute("SET LOCAL statement_timeout = '10s'")

            with conn.cursor() as cur:
                cur.execute(sql, params, prepare=True)

                if cur.description is None:
                    raise ValueError("The query did not return a result table.")

                columns = [col.name for col in cur.description]
                rows = cur.fetchmany(501)

                if len(rows) > 500:
                    raise ValueError(
                        "Query returned more than 500 rows. "
                        "Please add a LIMIT clause."
                    )

                return pd.DataFrame(rows, columns=columns)
