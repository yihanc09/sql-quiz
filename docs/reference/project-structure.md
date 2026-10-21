# Project structure

The root holds the README, environment template, launchers and platform configuration. Source code, maintenance commands, data, documentation and evidence have distinct homes.

## Directory ownership

| Path | Responsibility |
|---|---|
| `sql_quiz/` | Shared application services and HTTP/Streamlit interfaces |
| `frontend/` | Browser HTML, styles and JavaScript |
| `scripts/admin/` | Instructor database provisioning, permissions and audit maintenance |
| `scripts/data/` | CSV validation, knowledge generation and offline reference export |
| `scripts/rag/` | Vector indexing, retrieval, cloud verification and SQL-generation CLI |
| `requirements/` | Shared and optional local dependency manifests |
| `data/chinook/` | Eleven reproducible business-data CSVs |
| `data/schema.json` | Table/column/key/type contract |
| `knowledge/` | The 17-document retrieval corpus, excluding quiz answers and user data |
| `sql/` | Numbered database migrations, applied through explicit admin commands |
| `tests/unit/` | Offline service, API, authentication and configuration contracts |
| `tests/vector/` | Actual local Chroma persistence and similarity retrieval |
| `tests/integration/` | Live PostgreSQL/security checks using backend credentials |
| `tests/fixtures/` | Offline reference snapshot; production grading queries live data |
| `docs/guides/` | Setup, deployment, cloud/local retrieval and AI usage |
| `docs/reference/` | Structure and live-database design |
| `docs/evidence/` | Deployment records, actual screenshots and captured JSON examples |
| `docs/archive/` | Historical preparation and implementation handoff |
| `.github/workflows/` | CI jobs with GitHub Secrets for database checks |
| `.vscode/settings.json` | Workspace-only Explorer exclusions for generated/private files |

## Application modules

| Area | Modules |
|---|---|
| Entry points and UI | Root `web_server.py`, root `app.py`, `web.py`, `streamlit_app.py` |
| Identity and storage | `auth.py`, `web_sessions.py`, `runtime_config.py` |
| Database and quiz | `database.py`, `dataset.py`, `quiz.py`, `quiz_reference.py`, `grading.py` |
| RAG | `retrieval.py`, `cloud_retrieval.py`, `generation.py` |
| Asset paths | `paths.py` |

Keep shared services in `sql_quiz/`. Put executable maintenance tasks in the appropriate `scripts` subpackage and invoke them with `python -m scripts.<group>.<command>`. HTTP routes stay in `web.py`; frontend changes stay in `frontend/`.

The Vercel entry point remains `web_server:handler`. Root `app.py` remains the optional Streamlit launcher. These stable entry points are intentionally not moved into tool directories.

## Dependency environments

- Root `pyproject.toml`: production runtime dependencies and Vercel/pytest configuration.
- Root `requirements.txt`: cloud/web development and CI, including the thin Chroma client.
- `requirements/base.txt`: shared development/quiz dependencies.
- `requirements/local.txt`: full local Chroma and MiniLM environment; install instead of root `requirements.txt`.

See the [dependency guide](../../requirements/README.md). Never install full `chromadb` and `chromadb-client` together in one environment.

## Private and generated files

Root `.env` is the active backend configuration. Private deployment import data lives in `.local/deployment.env`; the legacy configuration backup lives in `.local/backups/.env.old`. The entire `.local/` directory is ignored and excluded from Vercel. No secret values belong in Git.

`.venv/`, `.venv-cloud/`, `.chroma/`, caches and bytecode remain workstation artifacts. Their locations are retained so virtual environments and local indexes continue to work; the workspace Explorer hides them. Use **Go to File** or the terminal to inspect a hidden path when needed.

## Stable knowledge provenance

The implementation is `scripts/data/build_knowledge.py`. A small `scripts/build_knowledge.py` compatibility entry point is intentionally retained because existing local/cloud documents cite it as their source. Keeping that real source entry point preserves the committed corpus fingerprint and existing vector indexes; this file reorganization does not require re-embedding.

## Where to edit

- Questions, points and hints: `sql_quiz/quiz.py`.
- Table contracts: `data/schema.json`; source CSVs are in `data/chinook/`.
- Knowledge rules/examples: `scripts/data/build_knowledge.py`, then `python -m scripts.data.build_knowledge` and explicitly reindex if the corpus changes.
- AI requests: `sql_quiz/generation.py`; cloud embeddings: `sql_quiz/cloud_retrieval.py`.
- Setup instructions: `docs/guides/`; verification records/images: `docs/evidence/`.

See [maintenance commands](../../scripts/README.md) for read-only versus write operations.
