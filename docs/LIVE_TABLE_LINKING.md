# Connecting the quiz to the uploaded Supabase tables

The active data source is now the user's 11 uploaded tables in `public`, not the older `chinook` copy. The existing five questions still total 20 points. They use seven tables; the remaining four are available in both UIs and the retrieval corpus for further questions.

| Question | Live source tables | Output |
|---|---|---|
| 1: Count Artists | `public.artist` | 1 row, `total_artists` |
| 2: Albums by Artist | `public.artist`, `public.album` | 5 rows, `artist`, `album_count` |
| 3: Average Track Duration | `public.genre`, `public.track` | 25 rows, `genre`, `avg_minutes` |
| 4: Top Spending Customers | `public.customer`, `public.invoice` | 5 rows, `first_name`, `last_name`, `total_spent` |
| 5: Most Popular Genres | `public.genre`, `public.track`, `public.invoice_line` | 5 rows, `genre`, `tracks_sold` |

## What “live answers” means

`sql_quiz/quiz.py` retains the instructor's SQL because the system needs a definition of the expected answer. It also owns the linked table names and explanatory hints shared by both frontends. This SQL is a query over business data, not a saved answer row.

- **Run query** executes the student's SQL against Supabase using `quiz_reader`.
- **Show expected SQL & live result** calls authenticated `POST /api/hint`. The server executes the selected instructor query and returns its current columns and rows, alongside the SQL. Refresh repeats the query.
- **Submit for grading** executes the student's SQL, separately executes the selected instructor SQL against the same database/reader, compares results, and saves the grade. Comparison checks column names, values and requested ordering; SQL text need not match.
- A reference-query failure does not fall back to a JSON file or save a grade. The student can still see their successfully executed result and retry.
- `tests/fixtures/expected_results.json` is now only an export for offline tests/documentation. Neither production hints nor grading reads it.

The student and reference executions use separate read-only transactions. Concurrent business-data changes between those executions can affect a comparison; this assignment's static sample dataset avoids that practical issue. Displayed hints are labeled with their refresh time, and grading always fetches a fresh reference instead of using the displayed hint cache.

Saved answers remain in `public.quiz_answers`, and audit events remain in `public.quiz_audit_log`. Those tables are separate from the business data and remain inaccessible to the query reader. Previously saved SQL is preserved as written; old drafts explicitly mentioning `chinook.` should be revised to `public.`. Old saved grades are historical until the user submits again.

## Supabase changes applied

`python -m scripts.link_public_tables --apply` was run on October 21, 2026. In a transaction, it:

1. Validated every uploaded row against all 11 local CSVs, including types and foreign-key integrity.
2. Converted employee reporting IDs from text to integer; converted employee and invoice dates from text to timestamp; converted prices/totals from floating point to `numeric(10,2)`.
3. Trimmed city whitespace to align the CSVs and live tables.
4. Added primary keys, required-column constraints, and foreign keys to the uploaded tables.
5. Granted the existing `quiz_reader` SELECT on exactly these business tables and added a reader-specific SELECT RLS policy. Supabase's existing RLS stays enabled; no anonymous-read policy was added.

The existing `chinook` tables, user answers, audit log, Auth configuration, and runtime secrets were preserved.

Read-only preflight and exact comparison:

```bash
python -m scripts.link_public_tables
python -m scripts.prepare_data --check-db
```

To repeat the configuration on this same uploaded-table setup:

```bash
python -m scripts.link_public_tables --apply
```

This script requires the existing configured administrator backend and `quiz_reader`, plus all 11 uploaded public tables. It is not a full new-project provisioner. Reapplication is idempotent for its own constraints and RLS policies. A row mismatch, unexpected primary key, lock conflict, type conversion failure, or constraint failure aborts the transaction.

## Use and validation

Start either interface after restarting any earlier Python server:

```bash
python web_server.py --port 8001
# Open http://localhost:8001

# Optional original Streamlit UI:
python -m streamlit run app.py
```

Sign in, open a question, and select **Show expected SQL & live result**. Type a query using `public.*`, run it, and submit for grading. The guide/reference now includes all 11 tables and their relationships.

Validation completed:

- **78 offline tests passed**, including changing live reference values, authentication for hints, no static fallback, no grade save on reference failure, and shared 11-table metadata.
- **36 hosted database/security tests passed**, including all five reference queries and all 11 table counts through the restricted reader. Current reference outputs have 1, 5, 25, 5, and 5 rows respectively.
- All 15,607 uploaded rows match the CSVs after normalization.
- JavaScript syntax and a lightweight frontend behavior check passed for displaying 11 tables, rendering live hints, preserving the editor draft, and escaping displayed SQL. No browser was available for visual layout verification in this session.

The Actions workflow includes these checks. The canonical source and the connected `yihanc09/sql-quiz` deployment repository are synchronized with separate English commits. Both workflows require their own reader-only `QUIZ_DATABASE_URL` Secret. The database configuration is already applied; pushing the deployment repository triggers Vercel. Consult Actions and Vercel for the current run status.

## RAG follow-up

The prepared 17-document knowledge corpus now describes `public` tables. The five quiz answers and user submissions are not indexed. Vector retrieval and AI SQL generation remain the next implementation phase; this live-table connection does not itself constitute RAG.
