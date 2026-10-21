# Retrieval knowledge sources

`documents.jsonl` is the prepared corpus for the next RAG implementation, not a vector database.

Rebuild from the full schema contract and curated semantics/examples:

```bash
python -m scripts.build_knowledge
```

Each JSONL record contains `id`, `text`, and flat `metadata` fields, suitable for subsequent Chroma ingestion. Index `text`, preserve IDs and metadata, and use vector similarity retrieval for each user question. There are no answer tables, user records, credentials, or complete quiz answers in this corpus. The few-shot queries are separate examples.

See [the preparation handoff](../docs/WEEK8_PREPARATION.md) for checks, architecture, hosting constraints, and remaining work.
