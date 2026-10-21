[![SQL Quiz CI](https://github.com/yihanc09/IDS706-SQL-Quiz/actions/workflows/test.yml/badge.svg)](https://github.com/yihanc09/IDS706-SQL-Quiz/actions/workflows/test.yml)

# IDS706 SQL Quiz

An interactive SQL practice application for **IDS706 Data Engineering**, built with an independent **HTML/CSS/JavaScript frontend**, a **Python backend**, and **Supabase PostgreSQL**. Students explore the Chinook Music Store database, use question-specific hints, run read-only SQL, receive automatic grading feedback, and resume saved work across sessions.

The frontend uses a professional **Duke Blue** palette, responsive layouts, question navigation, a SQL editor, and a results dashboard. The original Streamlit application is also retained.

**Frontend website:**

**Original Streamlit app:** [IDS706 SQL Quiz](https://ids706-sql-quiz.streamlit.app/)

**Local frontend preview:** [http://localhost:8000](http://localhost:8000)

## Project Overview

The quiz contains **five business-oriented SQL questions worth 20 points total**. Each answer is graded against reference results generated from the Chinook database. Students can save drafts, revise answers, submit individual questions for grading, and review their total score.

### Key Features

- **Independent frontend:** Duke Blue styling, responsive navigation, and dedicated guide, question, and results pages.
- **Authentication:** Sign up, sign in, and sign out through Supabase Auth.
- **Dataset guide:** Introduces seven Chinook tables; the database reference remains available on question pages.
- **Visible hints:** An always-visible **Hint** section sits below each question and above the SQL editor, explaining relevant tables, join fields, and the approach to aggregation or sorting.
- **SQL editor:** Supports per-question drafts, line numbers, tab indentation, and Ctrl/Cmd + Enter to run a query.
- **Interactive execution:** Inspect results from read-only PostgreSQL queries before submitting.
- **Automatic grading:** Each question earns 0 or 4 points based on its returned columns, values, and required row order.
- **Persistent progress:** Save drafts and graded submissions in Supabase and restore them after signing in again.
- **Results dashboard:** Review each question's status and the total score out of 20.
- **Parameterized application SQL:** Bind values separately from SQL text for audit writes, log inspection, and permission checks.
- **Audit logging:** Record who ran or saved a query, the question, SQL text, timestamp, and execution status.
- **Integrity checks:** Verify that student-facing roles cannot read, directly insert into, modify, delete, or truncate the audit log.

## Technology Stack

| Component | Technology |
|---|---|
| Independent frontend | HTML, CSS, JavaScript; no frontend build step |
| Local HTTP/API backend | Python `http.server` |
| Original application | Streamlit |
| Database and authentication | Supabase PostgreSQL and Supabase Auth |
| PostgreSQL driver | psycopg 3 |
| Query results and grading | pandas and Python |
| Automated tests | pytest |
| Continuous integration | GitHub Actions |
| Original app hosting | Streamlit Community Cloud |

## Quiz Content

| Question | Topic | Points |
|---|---|---:|
| 1 | Count all artists | 4 |
| 2 | Top five artists by album count | 4 |
| 3 | Average track duration by genre | 4 |
| 4 | Top five customers by total spending | 4 |
| 5 | Top five genres by tracks sold | 4 |
| **Total** | | **20** |

Questions and reference SQL are defined in [`quiz.py`](quiz.py). Expected output tables are stored in [`data/expected_results.json`](data/expected_results.json).

The quiz uses seven tables in the `chinook` schema:

| Table | Purpose | Relevant fields |
|---|---|---|
| `chinook.artist` | Musicians and bands | `artist_id`, `name` |
| `chinook.album` | Artist albums | `album_id`, `artist_id` |
| `chinook.track` | Individual tracks | `track_id`, `album_id`, `genre_id`, `milliseconds` |
| `chinook.genre` | Music categories | `genre_id`, `name` |
| `chinook.customer` | Store customers | `customer_id`, `first_name`, `last_name` |
| `chinook.invoice` | Customer purchases | `invoice_id`, `customer_id`, `total` |
| `chinook.invoice_line` | Tracks purchased | `invoice_id`, `track_id`, `quantity` |

## Application Workflow

1. Open the frontend and explore the dataset guide.
2. Sign in or create an account. Confirm your email if required by Supabase.
3. Choose a question and read its business scenario and **Hint** section.
4. Write SQL using the `chinook.` schema prefix. Select **Run query** to inspect the output.
5. Select **Save answer** to preserve a draft, or **Submit for grading** to evaluate and save the answer and score.
6. Navigate between questions and open **Quiz results** to review progress.
7. Sign out and sign back in to restore saved answers and grades.

In the independent frontend, visitors can preview the guide and questions without signing in. Running queries, saving answers, and grading require authentication. The original Streamlit interface requires sign-in before showing the quiz workspace.

Unsaved edits remain in browser memory while navigating between questions. Use **Save answer** before closing or refreshing the page. Editing an answer invalidates its displayed grade until it is submitted again; grades for other questions remain intact. Saving an unchanged graded answer preserves its grade. Submissions are not permanently locked.

## Local Setup

### 1. Install Dependencies

Python **3.12** is recommended and is used in CI. From the project directory:

```bash
python -m pip install -r requirements.txt
```

The independent frontend needs no Node.js installation, package installation, or build step.

### 2. Configure Environment Variables

Create a local `.env` using [`.env.example`](.env.example) as a reference:

```dotenv
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_publishable_or_anon_key
QUIZ_DATABASE_URL=your_quiz_reader_postgresql_connection_string
DATABASE_URL=your_trusted_backend_postgresql_connection_string
```

| Variable | Purpose |
|---|---|
| `SUPABASE_URL` | Supabase project endpoint |
| `SUPABASE_ANON_KEY` | Authentication and user-scoped answer API access |
| `QUIZ_DATABASE_URL` | Restricted `quiz_reader` connection for student SQL |
| `DATABASE_URL` | Trusted backend connection for audit writes, migrations, and instructor checks |

Keep `.env` and database credentials out of version control and frontend files. Never use an administrator connection for `QUIZ_DATABASE_URL`.

The Supabase project must already contain the Chinook dataset, `public.quiz_answers`, its per-user RLS policies, and the existing audit table. The included migration hardens this existing database; it is not a complete database provisioning script.

### 3. Apply the Audit Migration

For an environment that has not received the audit upgrade, run:

```bash
python audit_admin.py --apply
python audit_admin.py --check
```

`--apply` runs [`sql/001_audit_hardening.sql`](sql/001_audit_hardening.sql) against the database selected by `DATABASE_URL`. It changes the database, including a shared Supabase instance if configured, and retains existing answers and audit records. It adds SQL/source fields, hardens permissions, and installs append-only protections. The project database received this migration during validation.

### 4. Start the Independent Frontend

```bash
python web_server.py
```

Open [http://localhost:8000](http://localhost:8000). To use a different port:

```bash
python web_server.py --port 8001
```

The server binds only to `127.0.0.1`. Stop it with Ctrl+C. Restart after changing Python backend files; frontend file changes are loaded by refreshing the browser.

Login uses an HttpOnly, SameSite session cookie. Sessions expire after 12 hours and are cleared when the backend restarts, so a restart requires signing in again. Saved answers and grades remain in Supabase.

### 5. Run the Original Streamlit Interface (Optional)

```bash
python -m streamlit run app.py
```

Open the URL printed in the terminal, usually [http://localhost:8501](http://localhost:8501). Both interfaces reuse the authentication, query execution, question definitions, and grading modules.

## SQL Parameters and Execution Safety

Application-generated SQL uses `%s` placeholders and passes values separately to psycopg. Audit SQL, user IDs, actions, and question IDs are bound as data rather than interpolated with Python f-strings. Answer persistence uses structured Supabase API payloads.

For example:

```python
from database import run_query

result = run_query(
    "SELECT %s::text AS value",
    ("a value containing ' quotes",),
)
```

Students intentionally submit complete SQL statements. A full statement cannot be bound as a value parameter. Instead, student SQL runs through the restricted `quiz_reader` connection with layered controls:

- A read-only transaction.
- A 10-second statement timeout and a 500-row result limit.
- Application checks for a single SELECT/CTE-style statement.
- Driver preparation that rejects stacked statements, including two SELECTs, even outside the UI.
- Database permissions restricting access to student answers and audit records.

Administrator role probes use `psycopg.sql.Identifier` to compose role identifiers safely. These safeguards are not a complete sandbox for arbitrary SQL.

Reference: [psycopg parameter binding](https://www.psycopg.org/psycopg3/docs/basic/params.html).

## Audit Logging and Integrity

### What Is Recorded

Audit entries in `public.quiz_audit_log` contain:

| Field | Description |
|---|---|
| `id` | Audit entry identifier |
| `user_id` | Supabase user UUID |
| `action` | Run, submit, save, or update event |
| `question_id` | Quiz question identifier |
| `created_at` | Timestamp with time zone |
| `success` | Execution/save status; older records may have no status |
| `sql_answer` | SQL text for new backend and answer-trigger events |
| `source` | How the event was recorded |

| Source | Actions | Meaning |
|---|---|---|
| `server` | `RUN_QUERY`, `SUBMIT_QUERY` | Execution observed by the Python backend; identity comes from Supabase's verified user token |
| `answer_trigger` | `SAVE_ANSWER`, `UPDATE_ANSWER` | Recorded by the database in the same transaction as the saved answer |
| `client_rpc` | Legacy query events | Client-reported metadata retained for compatibility with the deployed Streamlit version |
| `legacy` | Historical events | Predates source tracking; missing historical SQL is not reconstructed |

Successful and failed SQL executions are logged. SQL rejected before execution is not an executed-query event. `SUBMIT_QUERY.success` describes execution success, not whether the answer earned points; grading is stored in `quiz_answers`.

Saving a revised answer appends a new event containing its SQL. Saving an unchanged graded answer is a no-op. Audit failures are reported separately from query/grade failures. Query execution and its audit INSERT use separate connections, so these two operations are not atomic; answer changes and their trigger-generated events are atomic.

### How the Log Is Protected

- RLS is enabled on the audit table.
- Direct audit-table privileges are revoked from `quiz_reader`, `authenticated`, `anon`, and `PUBLIC`.
- Students cannot directly read, insert, update, delete, or truncate audit records.
- The answer trigger uses a `SECURITY DEFINER` function with a fixed empty `search_path`; students cannot invoke it directly.
- Additional triggers reject UPDATE, DELETE, and TRUNCATE operations on the log.
- New query events are written by the trusted backend using parameterized SQL.
- The legacy RPC derives identity from `auth.uid()` and cannot supply a different user ID or forge `server` / `answer_trigger` sources. Its `client_rpc` events remain client-reported, not proof of execution.

Reference: [PostgreSQL function security](https://www.postgresql.org/docs/current/sql-createfunction.html).

### Instructor Commands

Verify permissions and append-only protection:

```bash
python audit_admin.py --check
```

The checker verifies effective privileges, administrative role flags, ownership, RLS, enabled triggers, and function execution privileges. It attempts actual UPDATE, DELETE, and TRUNCATE operations using the real taker connection and administrator-switched `authenticated` / `anon` roles. All probes run in transactions that force rollback. Only permission denials with SQLSTATE `42501` count as successful blocks; unrelated errors do not count as a pass.

Inspect recent entries, including SQL text:

```bash
python audit_admin.py --recent 20
```

The limit must be between 1 and 100. These commands require the backend `DATABASE_URL`; the integrity check also uses `QUIZ_DATABASE_URL`. Audit records are not exposed through a student-facing log endpoint.

## Testing and Continuous Integration

### Automated Tests

| Test file | Cases | Coverage |
|---|---:|---|
| `tests/test_quiz.py` | 7 | Question definitions and reference data |
| `tests/test_grading.py` | 8 | Correct results and grading edge cases |
| `tests/test_web_server.py` | 12 | Authentication boundaries, query validation, save/submit behavior, and audit calls |
| `tests/test_audit.py` | 9 | Parameter binding, verified audit identity, event validation, and integrity-probe connections |
| `tests/test_database_connection.py` | 1 | Live Chinook connectivity |
| `tests/test_sql_security.py` | 19 | Read-only restrictions, audit permissions, parameter payloads, and stacked-statement rejection |
| **Total** | **56** | **36 unit tests + 20 database tests** |

Run unit tests without a live database:

```bash
python -m pytest tests/test_quiz.py tests/test_grading.py tests/test_web_server.py tests/test_audit.py -v
```

Run database tests with a valid `QUIZ_DATABASE_URL`:

```bash
python -m pytest tests/test_database_connection.py tests/test_sql_security.py -v
```

Run all pytest tests:

```bash
python -m pytest -v
```

The **46-check administrator integrity verification** is a separate command, not part of the 56 pytest cases:

```bash
python audit_admin.py --check
```

### Verified Results

The following checks passed during local validation of this implementation:

| Check | Result |
|---|---|
| Unit tests | 36 passed |
| Live database integration/security tests | 20 passed |
| Audit integrity verification | 46 checks passed |
| Actual student-role UPDATE, DELETE, and TRUNCATE attempts | Rejected for `quiz_reader`, `authenticated`, and `anon` |
| Local frontend HTTP readiness | HTTP 200 at `http://localhost:8000` |

These results describe local validation, not a new production deployment or a newly completed GitHub Actions run.

### GitHub Actions

[`.github/workflows/test.yml`](.github/workflows/test.yml) defines two jobs on pushes and pull requests to `main`, and supports manual execution:

- **`unit-tests`:** Runs the four unit-test files, covering 36 cases.
- **`database-tests`:** Runs the two database-test files, covering 20 cases, using the `QUIZ_DATABASE_URL` repository secret.

Both jobs must pass for the workflow to complete successfully. Database security tests cover read-only execution, audit access restrictions, and trigger-function permissions.

The administrator integrity command runs explicitly outside CI. Administrator database credentials are not required by the configured CI jobs. Check the actual workflow run before reporting CI status.

## Project Structure

```text
IDS706-SQL-Quiz/
├── .github/
│   └── workflows/
│       └── test.yml
├── frontend/
│   ├── index.html                 # Independent frontend shell and sign-in dialog
│   ├── styles.css                 # Duke Blue theme and responsive layouts
│   └── app.js                     # Navigation, hints, editor, and API interactions
├── data/
│   └── expected_results.json      # Reference output tables
├── sql/
│   └── 001_audit_hardening.sql    # Audit schema and integrity migration
├── tests/
│   ├── test_quiz.py
│   ├── test_grading.py
│   ├── test_web_server.py
│   ├── test_audit.py
│   ├── test_database_connection.py
│   └── test_sql_security.py
├── web_server.py                  # Local HTTP server and authenticated API
├── app.py                         # Original Streamlit interface
├── auth.py                        # Supabase authentication, answers, and audit writes
├── database.py                    # Parameterized, prepared, read-only query execution
├── grading.py                     # Result-based grading
├── quiz.py                        # Question definitions and reference SQL
├── audit_admin.py                 # Instructor migration, integrity, and log commands
├── generate_expected_results.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Scope and Limitations

- This is an educational practice application. Answers can be revised, submissions are not locked, and reference SQL/results are included in the repository.
- The independent Python HTTP server is intended for local testing. Production hosting requires HTTPS, a production server, shared session storage, and rate limiting.
- The independent frontend has not been published. Its deployment URL is intentionally left blank above; the existing Streamlit URL refers to the original hosted version.
- Audit logs retain submitted SQL for instructor review. Do not include passwords or other secrets in quiz answers.
- Database administrators can change grants or disable triggers. Append-only controls protect against student-role edits; they are not cryptographic tamper proofing.
