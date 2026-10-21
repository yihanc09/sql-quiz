[![SQL Quiz CI](https://github.com/yihanc09/sql-quiz/actions/workflows/test.yml/badge.svg)](https://github.com/yihanc09/sql-quiz/actions/workflows/test.yml)

# SQL Quiz — Vercel Deployment

This repository deploys the SQL Quiz frontend and Python API to Vercel. The canonical coursework repository is [yihanc09/IDS706-SQL-Quiz](https://github.com/yihanc09/IDS706-SQL-Quiz). Runtime code, data contracts, tests, and supporting documentation are synchronized from that project.

A 20-point SQL quiz using Supabase PostgreSQL and Supabase Auth. Students sign in, write SQL against the uploaded Chinook music-store tables, inspect results, save drafts, and submit for grading. Reference SQL and hints are instructor-defined; expected results are queried live, not loaded from a saved answer table.

**Public application:** [sql-quiz-jade.vercel.app](https://sql-quiz-jade.vercel.app/)

The deployed web interface uses HTML/CSS/JavaScript and a Python HTTP backend. It now supports authenticated RAG SQL generation with Chroma Cloud and OpenAI. Supabase remains the live PostgreSQL database and authentication provider. The optional Streamlit interface supports the original SQL quiz.

## RAG architecture and usage

```text
Natural-language question
  → OpenAI text-embedding-3-small (1536 dimensions)
  → Chroma Cloud cosine vector retrieval (top 5 sources)
  → retrieved knowledge + question → OpenAI Responses API (gpt-4.1-mini)
  → generated PostgreSQL displayed in the Knowledge tab
```

Chroma stores 17 curated documents: eleven table schemas, four business/SQL rules, and two independent few-shot examples. Generation performs actual vector retrieval; it does not load the five instructor answers or student submissions into the prompt.

Sign in, open a question, and choose **Knowledge → Generate SQL**. Review the generated code and its sources. **Use in editor** replaces the current draft; **Run query** executes it through the existing restricted reader. **Submit answer** compares the result with the selected quiz question. Generation does not automatically run, save, or grade SQL; this project does not claim the automatic execution/validation extra credit.

The public workflow was verified on October 21, 2026: the artist-count question generated `SELECT COUNT(*) AS total_artists FROM public.artist;`, and a manual run returned `275`. See [deployment verification and CI evidence](docs/evidence/deployment-verification.md).

## Required RAG screenshot

Actual signed-in production question and generated SQL:

![Natural-language question and AI-generated SQL on the deployed website](docs/evidence/screenshots/week8-production-generated-sql.png)

[Additional production screenshot: executed SQL, 275 artists, and Chroma Cloud retrieval metadata](docs/evidence/screenshots/week8-production-cloud-result.png). This shows a manual execution check, not an automatic-validation feature.

## Run locally

Use Python 3.12 or newer. Run these commands from the repository root:

```bash
python -m pip install -r requirements.txt
# Create .env using .env.example and your existing Supabase configuration.
python web_server.py --port 8001
```

Open [localhost:8001](http://localhost:8001), sign in, select a question, and write SQL with the `public.` schema prefix. **Run query** shows the result. **Hint → Reference SQL & expected result → Load live reference** executes the instructor query. **Submit answer** compares the current result tables and saves the score.

The existing project uses `DATABASE_URL` and `DATABASE_PASSWORD` in `.env`. Its Supabase application and reader settings are stored in the backend-only `quiz_private.runtime_config` table. A fresh project also needs Auth, answer-table policies, and a restricted reader; see [setup and operations](docs/guides/setup-and-operations.md).

For cloud-backed RAG, also fill the OpenAI/Chroma fields in `.env.example` using your own backend credentials and set `CHROMA_MODE=cloud`. Build your cloud collection once with `python -m scripts.rag.index_knowledge --cloud`, then restart the server. See [cloud setup](docs/guides/chroma-cloud.md) for all eight settings and [local Chroma setup](docs/guides/chroma-local.md) if using local MiniLM instead. Never install the full and HTTP-only Chroma distributions together.

Optional Streamlit interface:

```bash
python -m streamlit run app.py
```

## Repository layout

```text
IDS706-SQL-Quiz/
├── app.py, web_server.py   # Stable Streamlit and HTTP launchers
├── sql_quiz/              # Auth, database, quiz, grading and RAG services
├── frontend/              # Browser HTML/CSS/JavaScript
├── scripts/
│   ├── admin/             # Database, permissions and audit administration
│   ├── data/              # CSV preparation, corpus generation and fixtures
│   └── rag/               # Indexing, retrieval and generation commands
├── requirements/          # Shared and optional local dependencies
├── data/                  # Eleven CSV tables and the schema contract
├── knowledge/             # Curated retrieval corpus; vectors stored separately
├── sql/                   # Numbered database migrations
├── tests/                 # Unit, integration, vector tests and fixtures
├── docs/
│   ├── guides/            # Setup and operation instructions
│   ├── reference/         # Project structure and database design
│   ├── evidence/          # Deployment records, screenshots and API examples
│   └── archive/           # Historical preparation notes
├── .github/workflows/     # CI with GitHub Secrets
├── .env.example           # Public configuration template
├── pyproject.toml         # Production runtime, Vercel entrypoint and pytest
├── requirements.txt       # Cloud/web development and CI environment
└── vercel.json            # Function settings and private-file exclusions
```

See [the file-by-file guide](docs/reference/project-structure.md) for where to make changes.

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
python -m scripts.data.prepare_data                    # Offline CSV integrity checks
python -m scripts.data.prepare_data --check-db         # Full-row live data comparison
python -m scripts.data.build_knowledge                  # Rebuild retrieval documents
```

Maintenance commands and their database effects are documented in [scripts/README.md](scripts/README.md). The Actions workflow runs unit and integration tests separately; the integration job reads the `QUIZ_DATABASE_URL` GitHub Secret. Never commit passwords, API keys or `.env` files.

## Documentation

- [File structure and editing guide](docs/reference/project-structure.md)
- [Local setup, deployment, configuration and audit operations](docs/guides/setup-and-operations.md)
- [Connecting the uploaded tables to live hints and grading](docs/reference/live-database.md)
- [Local ChromaDB setup and real vector retrieval](docs/guides/chroma-local.md)
- [Chroma Cloud setup](docs/guides/chroma-cloud.md)
- [OpenAI generation setup](docs/guides/sql-generation.md)
- [Week 8 RAG preparation and implementation status](docs/archive/week8-preparation.md)

- [Production Week 8 and original Week 7 screenshots](docs/evidence/screenshots.md)
