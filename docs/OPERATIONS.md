# Setup and operations

## Local configuration

Use Python 3.12+ and run commands from the repository root:

```bash
python -m pip install -r requirements.txt
```

The independent frontend requires no Node.js build step. `requirements.txt` includes Streamlit and pytest for local development; `pyproject.toml` contains the backend runtime dependencies used by Vercel.

Create `.env` using [the example](../.env.example):

```dotenv
DATABASE_URL=postgresql://postgres.YOUR_PROJECT_REF@YOUR_POOLER_HOST:5432/postgres?sslmode=require
DATABASE_PASSWORD=your_supabase_database_password
```

Use the Supabase session-mode pooler on port 5432 with `sslmode=require`. Omit the backend password from the URI; the driver receives it as a separate connection option. The backend must be able to read private settings and append audit events. Student queries use separate reader credentials.

The existing project stores `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `QUIZ_DATABASE_URL`, and `APP_SESSION_KEY` in `quiz_private.runtime_config`. Only the trusted backend can read that table. Legacy environment overrides for those settings still take precedence. `.env` remains at the repository root and is loaded using an explicit project path.

For first-time private-settings initialization in an already configured project:

```bash
python -m scripts.configure_runtime --init
python -m scripts.configure_runtime --check
```

Initialization applies [002_runtime_configuration.sql](../sql/002_runtime_configuration.sql), preserves existing settings, and generates a session encryption key if needed. If initial Auth/reader settings are only in the ignored local backup:

```bash
python -m scripts.configure_runtime --init --from-env .env.old
```

The backup is read without replacing the current administrator connection or printing credentials. A fresh project still needs its own Auth setup, per-user answer policies, and reader credentials; this command does not create a complete application database.

## Start and use the application

```bash
python web_server.py --port 8001
```

Open [localhost:8001](http://localhost:8001). The listener binds to `127.0.0.1`. Stop with Ctrl+C. Restart after Python changes; refreshing loads changed frontend files.

For the optional Streamlit interface:

```bash
python -m streamlit run app.py
```

Visitors can preview the independent frontend's questions and guide. Sign-in is required to run SQL, retrieve live reference results, save drafts, and submit grades. Streamlit requires sign-in before the quiz workspace.

Use `public.` table names. Run a query to inspect results, optionally show the reference SQL/current result, then submit for grading. Saved work is restored on sign-in. Editing an answer invalidates its displayed grade until resubmission; saving an unchanged graded answer preserves its grade. Unsaved edits remain only in browser memory.

Local sessions use an HttpOnly, SameSite cookie and process memory, with a 12-hour expiration. Restarting the listener clears local sessions. Vercel uses encrypted HttpOnly, Secure, SameSite cookies, allowing another function instance to restore the session. Saved answers and grades remain in Supabase.

## Student submission storage and login recovery

The application stores new student drafts and grades in `public.quiz_submissions`. This is empty application storage, not an instructor-answer dataset. It has ownership RLS, a user/question unique key, and audit/timestamp triggers. The removed `quiz_answers` table is not recreated and deleted records are not recovered.

For this project's existing Auth/audit setup:

```bash
python -m scripts.configure_submissions --apply
python -m scripts.configure_submissions --check
```

The first command applies `sql/003_submission_storage.sql`; the second checks permissions without writes. Authentication is independent of loading submission records: unavailable progress storage produces a warning, while a valid user can still log in and run SQL. Saving/grading persistence can fail separately until storage is repaired.

## Business data and live references

All 11 uploaded business tables are in `public`. `data/chinook/` contains the CSVs and `data/schema.json` defines types, keys, nullability and expected row counts.

```bash
python -m scripts.prepare_data
python -m scripts.prepare_data --check-db
python -m scripts.link_public_tables
```

The first command is offline; the latter two are read-only database checks. For type/key/reader configuration on the existing uploaded tables, use `python -m scripts.link_public_tables --apply`. For absent tables on a new data-only schema, `python -m scripts.prepare_data --apply` creates tables and fills empty ones, rejecting existing nonempty mismatches. These write commands preserve existing records and roll back on failure; they do not provision a fresh Auth application.

[quiz.py](../sql_quiz/quiz.py) defines the questions and reference SQL. Hints and grading fetch live results through [quiz_reference.py](../sql_quiz/quiz_reference.py). `tests/fixtures/expected_results.json` is an offline test snapshot and is not a runtime fallback. Export a new snapshot after intentional dataset/question changes:

```bash
python -m scripts.generate_expected_results
```

See [live-table linking](LIVE_TABLE_LINKING.md) for details and concurrency limitations.

## Deploy to Vercel

The canonical source is `yihanc09/IDS706-SQL-Quiz`. The existing Vercel project is connected to `yihanc09/sql-quiz`, branch `main`, with the repository root as Root Directory. Synchronize application changes to that deployment repository to update the public website. The configured entrypoint remains:

```toml
[tool.vercel]
entrypoint = "web_server:handler"
```

`web_server.py` is a thin export of the HTTP handler in `sql_quiz/web.py`. Importing the handler does not start a local listener. `app.py` is only the Streamlit launcher.

Use the Other framework preset if needed. Leave Build Command, Install Command and Output Directory at their defaults; do not use a server-start command as a build command or set the output directory to `frontend`.

Set `DATABASE_URL` and `DATABASE_PASSWORD` as backend environment variables. After initializing private settings, Auth configuration, reader credentials and session encryption are loaded from the private table. Use the session-mode pooler for both connections so prepared statements are supported.

`.python-version` selects Python 3.12. `vercel.json` keeps a 60-second function duration and excludes secrets, maintenance scripts, SQL migrations, documentation, tests and caches. Runtime package code, frontend assets and `data/schema.json` remain available. The runtime does not need the offline test snapshot.

Deploy the latest source and verify sign-in, live Hint, Run query, Save answer, Submit for grading, and restored progress. Directory cleanup alone does not update a hosted deployment.

References: [Vercel Python entrypoints](https://vercel.com/docs/functions/runtimes/python#python-entrypoints), [Supabase connections](https://supabase.com/docs/guides/database/connecting-to-postgres).

## Testing and CI

```bash
python -m pytest                         # Default: offline unit tests
python -m pytest tests/integration -v     # Live Supabase tests
python -m pytest tests/unit tests/integration -v  # Both suites
```

Pytest configuration is in `pyproject.toml`; caches go in ignored `.cache/pytest/`. Integration tests require the configured reader connection, either from private settings or a `QUIZ_DATABASE_URL` environment override.

[GitHub Actions](../.github/workflows/test.yml) has two separate jobs. The unit job runs `tests/unit`; the database job runs `tests/integration` and reads `QUIZ_DATABASE_URL` from GitHub Secrets. Administrator credentials are not required in CI. Repository Secrets are scoped independently: configure the restricted `QUIZ_DATABASE_URL` in both repositories when running both live integration workflows. The deployment repository has this reader-only Secret configured as well. Check the actual workflow run before reporting GitHub status.

## SQL execution and audit integrity

Application-owned SQL binds values with `%s` placeholders. Identifier composition uses `psycopg.sql.Identifier`. A student submits a complete SQL statement, which cannot itself be bound as a value. The execution boundary combines an independent reader, a read-only transaction, prepared-statement rejection of stacked statements, a 10-second timeout and a 500-row limit. The application additionally checks for a single SELECT/CTE-style query. This is an educational query environment rather than a complete arbitrary-SQL sandbox.

The audit table records user ID, question, action, timestamp, SQL text, success and event source:

| Source | Meaning |
|---|---|
| `server` | Backend-observed `RUN_QUERY` / `SUBMIT_QUERY`, with identity from a verified user token |
| `answer_trigger` | `SAVE_ANSWER` / `UPDATE_ANSWER` in the same transaction as persistence |
| `client_rpc` | Legacy client-reported events; retained for compatibility |
| `legacy` | Historical events; absent historical SQL is not reconstructed |

Execution success does not mean grading correctness. Successful and failed executions are logged; statements rejected before execution are not execution events. Query execution and audit writes use separate connections and are not atomic. Answer changes and trigger-generated audit entries are atomic. Audit failures are displayed separately from query/grade failures.

Direct audit-table privileges are revoked from `quiz_reader`, `authenticated`, `anon` and `PUBLIC`. RLS and append-only triggers protect the log. The answer trigger uses a SECURITY DEFINER function with a fixed empty search path; student roles cannot invoke it directly. The trusted backend writes query events using bound parameters. Legacy RPC identity comes from `auth.uid()` and cannot forge backend/trigger event sources.

Maintenance commands:

```bash
python -m scripts.audit_admin --apply
python -m scripts.audit_admin --check
python -m scripts.audit_admin --recent 20
```

`--apply` runs [001_audit_hardening.sql](../sql/001_audit_hardening.sql). `--check` verifies permissions, role flags, ownership, RLS, triggers and function execution rights. It probes UPDATE, DELETE and TRUNCATE using the real reader and role-switched authenticated/anon connections, forcing all probes to roll back; only SQLSTATE 42501 counts as a permission denial. `--recent` accepts 1–100 and prints audit records including SQL. No student-facing audit-reading endpoint is exposed.

Keep backend credentials and submitted SQL secrets private. Administrators can change permissions and disable triggers; append-only protections address student-role edits and are not cryptographic tamper proofing. Public deployments also need appropriate operational monitoring and rate limiting.

## RAG preparation

```bash
python -m scripts.build_knowledge
```

This rebuilds `knowledge/documents.jsonl` from schema metadata and curated business rules/examples. To create and query the actual local vector index, install the optional Python 3.12 environment and run:

```bash
.venv/bin/python -m scripts.index_knowledge
.venv/bin/python -m scripts.search_knowledge "What is the average track duration for each genre?"
.venv/bin/python web_server.py --port 8001
```

See [local Chroma setup](CHROMA_LOCAL.md) for installation and the retrieval inspector. Local retrieval and authenticated OpenAI generation are implemented; see [AI generation setup](AI_SQL_GENERATION.md). Chroma Cloud retrieval is now verified; see [cloud configuration](CHROMA_CLOUD.md). Public RAG deployment remains next. See [Week 8 preparation](WEEK8_PREPARATION.md) for remaining requirements.
