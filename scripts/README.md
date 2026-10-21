# Maintenance commands

Run from the repository root using `python -m scripts.<command>`. Application services live in `sql_quiz/`; these commands are for maintenance and are excluded from the Vercel function bundle.

| Command | Purpose | Effect |
|---|---|---|
| `python -m scripts.prepare_data` | Validate all 11 CSVs, types, counts, primary and foreign keys | Offline, read-only |
| `python -m scripts.prepare_data --check-db` | Compare every typed row with Supabase | Database read-only |
| `python -m scripts.prepare_data --apply` | Bootstrap missing tables and populate empty tables; reject nonempty mismatches | Writes database; rolls back on failure |
| `python -m scripts.link_public_tables` | Preflight the uploaded public tables and existing reader | Database read-only |
| `python -m scripts.link_public_tables --apply` | Normalize uploaded types, establish keys, SELECT grants and reader RLS policies | Writes database; retains existing records |
| `python -m scripts.configure_submissions --apply` | Create empty student submission storage, per-user RLS and audit triggers | Writes database; does not restore deleted legacy answers |
| `python -m scripts.configure_submissions --check` | Verify submission storage and role permissions | Database read-only |
| `python -m scripts.configure_runtime --check` | Verify private runtime-settings permissions | Database read-only |
| `python -m scripts.configure_runtime --init` | Apply private-settings migration and initialize existing local settings | Writes database |
| `python -m scripts.audit_admin --check` | Verify audit permissions and append-only protections | Database probes, all forced to roll back |
| `python -m scripts.audit_admin --apply` | Apply audit hardening migration | Writes database |
| `python -m scripts.audit_admin --recent 20` | Inspect recent audit entries | Database read-only; output includes submitted SQL |
| `python -m scripts.build_knowledge` | Build the 17 retrieval documents | Writes `knowledge/documents.jsonl` |
| `.venv/bin/python -m scripts.index_knowledge` | Embed curated documents and synchronize local Chroma | Writes ignored local vector index; first run downloads model |
| `.venv/bin/python -m scripts.search_knowledge "question"` | Embed a question and retrieve nearest knowledge vectors | Reads local Chroma; returns sources and distances |
| `.venv/bin/python -m scripts.generate_sql --check-config` | Validate OpenAI environment configuration | Offline; hides key values |
| `.venv/bin/python -m scripts.generate_sql "question"` | Retrieve Chroma context, then generate SQL with OpenAI | Sends the question and retrieved knowledge to OpenAI; no SQL execution |
| `.venv/bin/python -m scripts.index_knowledge --cloud` | Embed curated knowledge and index Chroma Cloud | Sends knowledge to OpenAI; writes application cloud collection |
| `.venv/bin/python -m scripts.check_cloud` | Verify cloud index metadata, corpus and count | Reads Chroma Cloud; no OpenAI calls |
| `python -m scripts.generate_expected_results` | Export current references for offline tests | Reads database; writes `tests/fixtures/expected_results.json` |

The database commands use the existing `.env`/private settings. Initializing a completely new Supabase project also requires its own Auth setup, answer table/policies and reader credentials; these are maintenance tools for the configured project.

See [operations](../docs/OPERATIONS.md) and [uploaded-table setup](../docs/LIVE_TABLE_LINKING.md) for details.
