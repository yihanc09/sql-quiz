# Maintenance commands

Run commands from the repository root. Application services live in `sql_quiz/`; maintenance commands are excluded from the Vercel function bundle. Commands have moved into the subpackages below; use these current module paths.

## Database administration

| Command | Purpose | Effect |
|---|---|---|
| `python -m scripts.admin.link_public_tables` | Preflight the uploaded public tables and existing reader | Database read-only |
| `python -m scripts.admin.link_public_tables --apply` | Normalize uploaded types, establish keys, SELECT grants and reader RLS policies | Writes database; retains existing records |
| `python -m scripts.admin.configure_submissions --apply` | Create empty student submission storage, per-user RLS and audit triggers | Writes database; does not restore deleted legacy answers |
| `python -m scripts.admin.configure_submissions --check` | Verify submission storage and role permissions | Database read-only |
| `python -m scripts.admin.configure_runtime --check` | Verify private runtime-settings permissions | Database read-only |
| `python -m scripts.admin.configure_runtime --init` | Apply private-settings migration and initialize existing local settings | Writes database |
| `python -m scripts.admin.audit_admin --check` | Verify audit permissions and append-only protections | Database probes, all forced to roll back |
| `python -m scripts.admin.audit_admin --apply` | Apply audit hardening migration | Writes database |
| `python -m scripts.admin.audit_admin --recent 20` | Inspect recent audit entries | Database read-only; output includes submitted SQL |

## Data preparation

| Command | Purpose | Effect |
|---|---|---|
| `python -m scripts.data.prepare_data` | Validate all 11 CSVs, types, counts, primary and foreign keys | Offline, read-only |
| `python -m scripts.data.prepare_data --check-db` | Compare every typed row with Supabase | Database read-only |
| `python -m scripts.data.prepare_data --apply` | Bootstrap missing tables and populate empty tables; reject nonempty mismatches | Writes database; rolls back on failure |
| `python -m scripts.data.build_knowledge` | Build the 17 retrieval documents | Writes `knowledge/documents.jsonl` |
| `python -m scripts.data.generate_expected_results` | Export current references for offline tests | Reads database; writes `tests/fixtures/expected_results.json` |

## RAG development and verification

| Command | Purpose | Effect |
|---|---|---|
| `.venv/bin/python -m scripts.rag.index_knowledge` | Embed curated documents and synchronize local Chroma | Writes ignored local vector index; first run downloads model |
| `.venv/bin/python -m scripts.rag.search_knowledge "question"` | Embed a question and retrieve nearest knowledge vectors | Reads local Chroma; returns sources and distances |
| `.venv/bin/python -m scripts.rag.generate_sql --check-config` | Validate OpenAI environment configuration | Offline; hides key values |
| `.venv/bin/python -m scripts.rag.generate_sql "question"` | Retrieve Chroma context, then generate SQL with OpenAI | Sends the question and retrieved knowledge to OpenAI; no SQL execution |
| `.venv/bin/python -m scripts.rag.index_knowledge --cloud` | Embed curated knowledge and index Chroma Cloud | Sends knowledge to OpenAI; writes application cloud collection |
| `.venv/bin/python -m scripts.rag.check_cloud` | Verify cloud index metadata, corpus and count | Reads Chroma Cloud; no OpenAI calls |

`scripts/build_knowledge.py` is the one stable compatibility entry point. Existing Chroma documents cite it as their source; the implementation is now in `scripts/data/build_knowledge.py`. Keeping it preserves corpus metadata and avoids an unnecessary reindex.

Use root `requirements.txt` for a cloud-only environment or `requirements/local.txt` for full local Chroma. The RAG commands select the configured backend; `--cloud` explicitly selects Chroma Cloud for that command. No indexing or SQL generation runs during import or application startup.

Database maintenance uses backend `.env`/private settings. A fresh Supabase project also needs Auth setup, per-user submission policies and reader credentials. See [setup and operations](../docs/guides/setup-and-operations.md) and [live database reference](../docs/reference/live-database.md).
