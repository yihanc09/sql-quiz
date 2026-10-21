# Retrieval knowledge sources

`documents.jsonl` is the curated source corpus. Its embeddings are stored separately in the local Chroma database under ignored `.chroma/`.

Rebuild from the full schema contract and curated semantics/examples:

```bash
python -m scripts.build_knowledge
```

Each JSONL record contains `id`, `text`, and flat `metadata` fields, used by the Chroma ingestion command. Index `text`, preserve IDs and metadata, and use vector similarity retrieval for each user question. There are no answer tables, user records, credentials, or complete quiz answers in this corpus. The few-shot queries are separate examples.

See [the preparation handoff](../docs/WEEK8_PREPARATION.md) for checks, architecture, hosting constraints, and remaining work.

Build and search the actual vector index after installing `requirements-rag.txt`:

```bash
.venv/bin/python -m scripts.index_knowledge
.venv/bin/python -m scripts.search_knowledge "Which artists have the largest album catalogs?"
```

See [local Chroma retrieval](../docs/CHROMA_LOCAL.md) for the model, persistence, validation and deployment boundaries.
