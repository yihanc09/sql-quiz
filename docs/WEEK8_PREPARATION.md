# Week 8 preparation and handoff

## Current status

Local ChromaDB retrieval is now implemented and verified over the 17-document corpus using 384-dimensional MiniLM embeddings. See [CHROMA_LOCAL.md](CHROMA_LOCAL.md) for installation, indexing, the web inspector and a real retrieval example. OpenAI SQL generation is implemented and a real local request passed. See [AI_SQL_GENERATION.md](AI_SQL_GENERATION.md). Chroma Cloud indexing and cloud-backed RAG have also passed real CLI requests; see [CHROMA_CLOUD.md](CHROMA_CLOUD.md). The public RAG deployment and authenticated browser verification are also complete; see [DEPLOYMENT_VERIFICATION.md](DEPLOYMENT_VERIFICATION.md).

## What was verified

**Update:** the user subsequently uploaded a new set of tables to `public`. These are now the active source. See [the live-table linking notes](LIVE_TABLE_LINKING.md); the older `chinook` copy remains intact.

On October 21, 2026, read-only checks against the existing Supabase project confirmed:

- All 11 Chinook business tables already exist. This database is not just a collection of quiz answers.
- The CSVs have 15,607 rows in total. Types, primary keys, and all foreign keys pass local validation.
- Eight CSV city values had a trailing space (`Edinburgh `): customer 54 and invoices 20, 141, 152, 207, 336, 359, 381. Only these CSV values were cleaned to match the existing database. No hosted data was changed.
- After cleaning, all 11 tables match the hosted database row-for-row, including types and NULLs. The restricted reader can query all 11 tables.
- The five existing reference SQL queries execute through the restricted reader and match the saved result tables.
- The first preparation validation passed 64 offline tests and 20 hosted database/security tests. The subsequent public-table linking has separate verification described in [LIVE_TABLE_LINKING.md](LIVE_TABLE_LINKING.md). The new bootstrap write path was not executed against the shared database.
- Q3's grading now enforces its requested alphabetical order, instead of accepting arbitrary genre ordering.

The original standard SQL and expected results are legitimate grading fixtures. They do not need to be deleted. Student submissions belong in `public.quiz_submissions`, separate from business data. The deleted legacy `quiz_answers` table is no longer used. Neither should be used as the source of truth for schema retrieval.

## Separate the three kinds of data

| Layer | Source | Use |
|---|---|---|
| Live business records | Supabase `public.*`; reproducible CSVs in `data/chinook/` | Execute SQL and show actual result tables |
| Grading | `sql_quiz/quiz.py` + live queries through `sql_quiz/quiz_reference.py` | Current hint output and result comparison; JSON snapshot is offline only |
| Retrieval knowledge | `knowledge/documents.jsonl` | Embed and retrieve table structures, relationships, semantics, and two separate examples |

`data/schema.json` describes every column and key, expected row counts, nullability, and PostgreSQL types. The active public schema uses `text` strings and `bigint` IDs; uploaded text dates and floating-point money were normalized to timestamps and exact numerics. CSV `YYYY/M/D` values are parsed as timestamps; money uses `Decimal`; empty optional fields become SQL NULL. No CSV data is silently stripped or otherwise rewritten during loading.

## Reproduce the preparation

```bash
python -m pip install -r requirements.txt
python -m scripts.prepare_data
python -m scripts.build_knowledge
python -m pytest tests/unit/test_data_preparation.py tests/unit/test_grading.py -q
```

The default preparation command performs no network requests. It checks exact headers and row counts, value types, required fields, duplicate keys, and orphan foreign keys. Knowledge generation is deterministic and does not require an API key.

To compare every typed CSV row against the current hosted database:

```bash
python -m scripts.prepare_data --check-db
```

This uses the existing backend `.env` configuration and a read-only, repeatable-read transaction. It prints counts and mismatch counts, without customer records or credentials. Counts alone do not prove dataset equality.

For a new empty database, an explicit bootstrap command is available:

```bash
python -m scripts.prepare_data --apply
```

It creates missing Chinook tables with primary and foreign keys, and inserts data using bound parameters in dependency order. Existing nonempty tables must match the CSVs exactly; mismatches abort and roll back the entire transaction. It never drops, truncates, updates, or deletes existing rows. It does not provision Auth, quiz answer tables, runtime secrets, or reader credentials for a new project. The current project already has those components and does not need reimporting.

To revalidate the hosted execution boundary with the existing reader configuration:

```bash
python -m pytest tests/integration -v
```

The updated Actions workflow also runs the new offline dataset/knowledge checks. An actual new Actions run requires pushing these changes; local passing tests do not establish that a new workflow ran on GitHub.

## Planned RAG integration

The next implementation should follow:

```text
Authenticated natural-language question
  -> embed the question
  -> ChromaDB similarity query (retrieve relevant knowledge document IDs/text/distances)
  -> AI API receives question + retrieved context
  -> generated PostgreSQL shown in the SQL editor
  -> optional existing read-only execution + result comparison
```

The corpus currently contains 17 documents: 11 table documents, four business/rules documents, and two examples different from the five quiz reference queries. Each has a stable ID and source metadata. Do not indiscriminately index the repository: runtime secrets, user answers, audit logs, and grading fixtures are excluded from this corpus.

**Local and public cloud-backed RAG are implemented and verified.** The application embeds questions, queries Chroma, and calls the OpenAI Responses API through authenticated `/api/generate`. A real local generated response is recorded in `docs/examples/openai_generation.json`.

For the deployed Vercel application, prefer a remote Chroma service (cloud or a separately hosted persistent Chroma server). A local persistent Chroma directory is suitable for development or a persistent server host. Vercel's filesystem does not provide durable shared writes across function instances; writing an index there on every request is not a dependable deployment design. A remote service also avoids bundling local model weights into the current small Python deployment.

OpenAI is the selected provider; set backend `OPENAI_API_KEY` and optional `OPENAI_MODEL` as described in the generation guide. The local embedding model is already fixed at all-MiniLM-L6-v2; a future cloud embedding provider may require a new collection and reindexing. Use the same embedding model/version/dimensions for ingestion and question retrieval, with reindexing when changed. Keep API keys on the backend in environment variables, never in frontend JavaScript or commits. Remote Chroma credentials must also remain on the backend.

Expose retrieval evidence (source IDs or table names) beside generated SQL so the pipeline is reviewable. Keep generation behind the existing verified login boundary. Generated SQL must use the existing restricted reader and timeout/row limits if execution is added; never execute it with the backend administrator connection.

## Submission status

- Chroma Cloud/OpenAI credentials are configured as Production Secrets in Vercel.
- Both repositories contain the generation feature, retrieval integration, UI and setup documentation.
- The deployed question → retrieval → AI → SQL flow passed authenticated browser verification.
- The README includes an actual production question/generated-SQL screenshot.
- Manual execution of the generated count query returned 275. Automatic execution/validation extra credit is not implemented.
- Submit the canonical GitHub repository URL from the README. CI/build and screenshot evidence are linked in [deployment verification](DEPLOYMENT_VERIFICATION.md).

## Deployment references

The hosting recommendation above follows [Vercel’s guidance to use persistent storage for writes](https://vercel.com/kb/guide/how-can-i-use-files-in-serverless-functions) and [Chroma’s documented cloud/server client options](https://docs.trychroma.com/reference/python). The remote Chroma choice is a deployment recommendation; it has not yet been provisioned.
