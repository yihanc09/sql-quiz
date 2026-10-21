# Retrieval knowledge corpus

`documents.jsonl` contains 17 curated documents: eleven table schemas, four business/SQL rules and two independent examples. Each record has a stable ID, retrieval text and flat source metadata. Instructor answers, student work, audit records and credentials are excluded.

```bash
python -m scripts.data.build_knowledge
python -m scripts.rag.index_knowledge --cloud
python -m scripts.rag.search_knowledge --cloud "Which tables connect customers to purchases?"
```

The source corpus is committed; vectors live in Chroma Cloud or an ignored local `.chroma/` directory. Rebuild and explicitly reindex after changing the corpus. Existing provenance refers to the stable `scripts/build_knowledge.py` entry point, which delegates to `scripts/data/build_knowledge.py`.

See [cloud retrieval](../docs/guides/chroma-cloud.md), [optional local retrieval](../docs/guides/chroma-local.md) and [AI generation](../docs/guides/sql-generation.md).
