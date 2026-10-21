[![SQL Quiz CI](https://github.com/yihanc09/sql-quiz/actions/workflows/test.yml/badge.svg)](https://github.com/yihanc09/sql-quiz/actions/workflows/test.yml)

# SQL Quiz — Vercel Deployment

This repository deploys the SQL Quiz frontend and Python API to Vercel. The canonical coursework repository is [yihanc09/IDS706-SQL-Quiz](https://github.com/yihanc09/IDS706-SQL-Quiz). Runtime code, data contracts, tests, and supporting documentation are synchronized from that project.

A 20-point SQL quiz using Supabase PostgreSQL and Supabase Auth. Students sign in, write SQL against the uploaded Chinook music-store tables, inspect results, save drafts, and submit for grading. Reference SQL and hints are instructor-defined; expected results are queried live, not loaded from a saved answer table.

**Public application:** [sql-quiz-jade.vercel.app](https://sql-quiz-jade.vercel.app/)

The main interface uses HTML/CSS/JavaScript and a Python HTTP backend. An optional Streamlit interface shares the same services. Week 8 preparation includes a 17-document retrieval corpus; vector retrieval and AI SQL generation are not implemented yet.

## Run locally

Use Python 3.12 or newer. Run these commands from the repository root:

```bash
python -m pip install -r requirements.txt
# Create .env using .env.example and your existing Supabase configuration.
python web_server.py --port 8001
```

Open [localhost:8001](http://localhost:8001), sign in, select a question, and write SQL with the `public.` schema prefix. **Run query** shows the result. **Show expected SQL & live result** executes the instructor query. **Submit for grading** compares the current result tables and saves the score.

The existing project uses `DATABASE_URL` and `DATABASE_PASSWORD` in `.env`. Its remaining settings are stored in the backend-only `quiz_private.runtime_config` table. A fresh project also needs Auth, answer-table policies, and a restricted reader; see [setup and operations](docs/OPERATIONS.md).

Optional Streamlit interface:

```bash
python -m streamlit run app.py
```

## Repository layout

```text
IDS706-SQL-Quiz/
├── app.py                  # Thin Streamlit launcher
├── web_server.py           # Thin local/Vercel launcher
├── sql_quiz/               # Application code: auth, SQL execution, quiz, grading, APIs
├── frontend/               # HTML, CSS and browser JavaScript
├── scripts/                # Database administration and data/knowledge commands
├── data/
│   ├── chinook/            # 11 business-data CSVs (15,607 rows)
│   └── schema.json         # Column types, keys, relationships and expected counts
├── knowledge/              # Prepared retrieval documents; not a vector database
├── sql/                    # Versioned database migrations
├── tests/
│   ├── unit/               # Offline tests
│   ├── integration/        # Live Supabase and database security tests
│   └── fixtures/           # Offline reference-result snapshot
├── docs/                   # Structure, setup, live-table linking and RAG preparation
├── .github/workflows/      # CI, including database tests using GitHub Secrets
├── .env.example            # Configuration template; real .env stays untracked
├── pyproject.toml          # Runtime dependencies, Vercel entrypoint, pytest configuration
├── requirements.txt        # Runtime plus local Streamlit/test dependencies
└── vercel.json             # Function configuration and bundle exclusions
```

See [the file-by-file guide](docs/STRUCTURE.md) for where to make changes.

## Quiz and database

All 11 uploaded tables are in the `public` schema. Five questions use seven of them:

| Question | Source tables | Points |
|---|---|---:|
| Count Artists | `artist` | 4 |
| Albums by Artist | `artist`, `album` | 4 |
| Average Track Duration | `genre`, `track` | 4 |
| Top Spending Customers | `customer`, `invoice` | 4 |
| Most Popular Genres | `genre`, `track`, `invoice_line` | 4 |
| **Total** | | **20** |

Questions, hints, linked table names and reference SQL live in [sql_quiz/quiz.py](sql_quiz/quiz.py). [quiz_reference.py](sql_quiz/quiz_reference.py) executes the reference queries using the restricted reader. [grading.py](sql_quiz/grading.py) compares columns, values and requested ordering. The snapshot in `tests/fixtures/` is for offline tests only.

Student drafts and grades are stored in `public.quiz_submissions`, protected by per-user RLS. This table starts empty and does not hold instructor solutions. Login and query execution remain available if progress storage is unavailable.

Student queries use read-only transactions, prepared statements, a 10-second timeout and a 500-row limit. Saved submissions and audit logs are separate from business data and inaccessible to the query reader.

## Common commands

```bash
python -m pytest                                  # Offline unit tests
python -m pytest tests/integration -v              # Requires Supabase connectivity
python -m scripts.prepare_data                    # Offline CSV integrity checks
python -m scripts.prepare_data --check-db         # Full-row live data comparison
python -m scripts.build_knowledge                  # Rebuild retrieval documents
```

Maintenance commands and their database effects are documented in [scripts/README.md](scripts/README.md). The Actions workflow runs unit and integration tests separately; the integration job reads the `QUIZ_DATABASE_URL` GitHub Secret. Never commit passwords, API keys or `.env` files.

## Documentation

- [File structure and editing guide](docs/STRUCTURE.md)
- [Local setup, deployment, configuration and audit operations](docs/OPERATIONS.md)
- [Connecting the uploaded tables to live hints and grading](docs/LIVE_TABLE_LINKING.md)
- [Week 8 RAG preparation and remaining requirements](docs/WEEK8_PREPARATION.md)

- [Original Week 7 application screenshots](docs/SCREENSHOTS.md)
