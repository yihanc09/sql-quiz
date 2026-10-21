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
| `python -m scripts.generate_expected_results` | Export current references for offline tests | Reads database; writes `tests/fixtures/expected_results.json` |

The database commands use the existing `.env`/private settings. Initializing a completely new Supabase project also requires its own Auth setup, answer table/policies and reader credentials; these are maintenance tools for the configured project.

See [operations](../docs/OPERATIONS.md) and [uploaded-table setup](../docs/LIVE_TABLE_LINKING.md) for details.
