# Repository structure and editing guide

The repository root contains launchers, project documentation and tool configuration. Application services, maintenance commands and tests have separate directories.

## Application package: `sql_quiz/`

| Module | Responsibility |
|---|---|
| `web.py` | HTTP routes, verified sessions, query/save/grading/live-hint APIs |
| `streamlit_app.py` | Original Streamlit user interface |
| `auth.py` | Supabase authentication, answer persistence and query audit writes |
| `database.py` | Independent reader connection, bound parameters, timeouts and row limits |
| `quiz.py` | Five questions, points, hints, reference SQL and linked tables |
| `quiz_reference.py` | Live execution of reference SQL |
| `retrieval.py` | Backend selection, local Chroma, shared index lifecycle and semantic search |
| `cloud_retrieval.py` | Chroma Cloud client, backend credential validation and OpenAI embeddings |
| `generation.py` | Retrieve context, call OpenAI Responses, parse SQL and sanitize provider errors |
| `grading.py` | Compare result columns, values and requested ordering |
| `dataset.py` | CSV type conversion, key validation and full-row database comparison |
| `runtime_config.py` | Root `.env` and backend-only database settings |
| `web_sessions.py` | Encrypted Vercel sessions and expiration checks |
| `paths.py` | Central paths for frontend, data, knowledge and migrations |

`web_server.py` and `app.py` are thin HTTP and Streamlit launchers. The Vercel entrypoint remains `web_server:handler`. The Streamlit launcher re-executes its UI module on every rerun.

## Supporting directories

| Path | Contents |
|---|---|
| `frontend/` | HTML shell, CSS styles and browser interaction code |
| `scripts/` | Maintenance commands, invoked with `python -m scripts.<name>` |
| `data/chinook/` | All 11 business-data CSVs, previously in `data/Chinook_CSV/` |
| `data/schema.json` | Column types, nullability, keys, relationships and expected counts |
| `knowledge/` | Curated retrieval documents; generated vector storage lives in ignored `.chroma/` |
| `sql/` | Numbered database migrations |
| `tests/unit/` | Offline tests without account/network requirements |
| `tests/vector/` | Native Chroma tests using small offline vectors |
| `tests/integration/` | Live Supabase query and security tests |
| `tests/fixtures/` | Offline reference-result snapshot, unused by production grading |
| `docs/` | Structure, operations, live-data linking and RAG preparation |
| `.github/workflows/` | GitHub Actions workflows |

## Where to make changes

- **Questions and hints:** edit `sql_quiz/quiz.py`; both interfaces use these definitions.
- **Web layout:** edit `frontend/`.
- **HTTP and RAG endpoints:** edit `sql_quiz/web.py`; place new application services in `sql_quiz/`.
- **Retrieval knowledge:** edit `data/schema.json` or `scripts/build_knowledge.py`, then run `python -m scripts.build_knowledge`.
- **Database maintenance:** consult `scripts/README.md` to distinguish read-only checks from write operations.
- **Validation:** `python -m pytest` runs offline tests; `python -m pytest tests/integration` runs the live suite.

Student work is stored in `public.quiz_submissions`; instructor reference SQL stays in `sql_quiz/quiz.py`. Use `python -m scripts.configure_submissions --check` to inspect submission storage permissions.

Local `.env` files and private configuration backups remain untracked. Python imports use `sql_quiz.*` and `scripts.*`. Asset paths resolve from the repository location rather than the caller's working directory.
