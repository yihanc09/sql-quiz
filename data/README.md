# Chinook business data

| Path | Purpose |
|---|---|
| `chinook/*.csv` | Eleven business tables, 15,607 rows in total |
| `schema.json` | Expected headers, PostgreSQL types, nullability, row counts and relationships |

These files reproduce the uploaded Supabase `public` tables. They contain business records, not instructor SQL answers, student submissions or credentials. Production queries read Supabase over the network; CSVs are not a replacement database.

Run offline validation with `python -m scripts.data.prepare_data`. Compare against the hosted database with `python -m scripts.data.prepare_data --check-db`. Both are read-only. The separate `--apply` command can bootstrap missing tables and empty data; consult [maintenance commands](../scripts/README.md) before using it.

Expected quiz results for offline tests are in `tests/fixtures/`; retrieval knowledge is in `knowledge/`. See [live database reference](../docs/reference/live-database.md).
