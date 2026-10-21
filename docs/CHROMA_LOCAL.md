# Local Chroma vector retrieval

This stage implements actual embeddings, a persistent Chroma vector index and nearest-neighbor retrieval. The separate [OpenAI generation service](AI_SQL_GENERATION.md) now uses this retrieval output to produce SQL. The user chose local retrieval first; cloud integration is now available through the separate [Chroma Cloud path](CHROMA_CLOUD.md).

## Run

Use Python 3.12 for the tested local environment:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-rag.txt
.venv/bin/python -m scripts.build_knowledge
.venv/bin/python -m scripts.index_knowledge
.venv/bin/python -m scripts.search_knowledge "What is the average track duration in minutes for each genre?"
.venv/bin/python web_server.py --port 8001
```

Open [localhost:8001](http://localhost:8001), sign in, and open a question. Choose **Knowledge** in the learning toolkit, enter a natural-language question, and select **Search knowledge**. Matching sources appear as expandable cards; **Retrieval details** contains model and index information. It does not fill or execute the SQL editor.

## Quiz workspace

The question and SQL editor form the main column, followed by query results. A sticky desktop toolkit groups **Hint**, **Knowledge**, and **Schema** into tabs with their own scroll area. Hint reference SQL/results and retrieved source text expand on demand, preserving space for the answer.

At widths of 1100px or less, use the question's **Hint**, **Knowledge**, or table shortcuts to open the toolkit as a dismissible dialog. On phones it appears as a bottom sheet. Table chips open the matching schema entry; the schema tab searches table and column names. Switching tools preserves SQL and search drafts. Tab labels support arrow-key navigation, and Escape closes the compact dialog.

Run the server with `.venv/bin/python`, since the original system Python may not have Chroma installed. A server restart clears local in-memory login sessions; sign in again with the existing account.

The first index build downloads Chroma's default ONNX model (about 79 MB) into its normal user cache, `~/.cache/chroma/`. Later indexing and retrieval use cached model files. No embedding API key or paid model API is required for this local stage.

## Data flow

```text
17 curated knowledge documents
  -> all-MiniLM-L6-v2 embedding model
  -> 384-dimensional dense vectors
  -> persistent Chroma collection, cosine distance

Natural-language question
  -> the same embedding model
  -> Chroma collection.query(query_embeddings=...)
  -> ranked document IDs + text + metadata + distances
```

The collection is `chinook_knowledge_minilm_v1`. SQLite/index files live in ignored `.chroma/`. The 17 inputs comprise 11 schema documents, four semantics/rules documents and two independent examples. Business rows remain in Supabase. Grading fixtures, student submissions, audit records and credentials are excluded from the retrieval corpus.

A [real retrieval example](examples/chroma_retrieval.json) was produced with the CLI, including vector dimensions, corpus fingerprint, returned documents and measured distances. Distances are not answer confidence or correctness probabilities. Retrieval accuracy is not guaranteed.

## Implementation

| File | Purpose |
|---|---|
| `sql_quiz/retrieval.py` | Lazy dependency loading, local Chroma client, explicit embeddings, indexing and querying |
| `scripts/index_knowledge.py` | Build/update the persistent vector collection |
| `scripts/search_knowledge.py` | Run real similarity search from the command line |
| `requirements-rag.txt` | Optional local dependencies, including tested Chroma 1.5.9 |
| `tests/vector/` | Native Chroma persistence, vector ranking and update tests without model downloads |
| `POST /api/retrieve` | Authenticated retrieval endpoint; no SQL execution or generation |

Indexing upserts stable document IDs and removes obsolete documents from this generated collection. Running it twice does not duplicate documents. A corpus fingerprint and embedding-model/dimension metadata reject stale or incompatible indexes rather than silently mixing versions. A failed model download leaves an existing ready index intact; an interrupted database update marks the collection incomplete until rebuilt.

Rebuild after editing source schema or curated knowledge:

```bash
.venv/bin/python -m scripts.build_knowledge
.venv/bin/python -m scripts.index_knowledge
```

Optional environment settings, shown in `.env.example`:

```dotenv
CHROMA_LOCAL_PATH=.chroma
CHROMA_COLLECTION=chinook_knowledge_minilm_v1
```

Relative paths resolve from the repository root. Changing embedding models requires a new collection; the current implementation deliberately fixes the model at all-MiniLM-L6-v2 for matching ingestion/query embeddings.

## Validation

```bash
.venv/bin/python -m pytest tests/unit tests/vector -q
```

The native tests use explicit small vectors with Chroma itself, requiring neither an AI API key nor a model download. A separate `vector-tests` job is defined in GitHub Actions for the next repository update. They check nearest-neighbor ranking for queries with no shared document words, idempotent indexing, obsolete-document cleanup, persistence and model/corpus mismatch handling. API tests enforce login and verify that retrieval never runs SQL.

Separately, all five quiz questions were embedded with the real MiniLM model and queried against the 17-document collection; each returned at least one relevant schema document. This is a smoke check, not an accuracy benchmark.

## Next stages

1. Verify the integrated [OpenAI generation workflow](AI_SQL_GENERATION.md) locally.
2. Use the verified [Chroma Cloud path](CHROMA_CLOUD.md) for remote storage and deployment-compatible embeddings.
3. Verify the full flow on the deployed site and capture the required question/generated-SQL screenshot.

The current public Vercel site has not received this local-only feature. `VERCEL` deployments default to the cloud path and explicitly refuse local vector storage; the existing quiz can continue to function without the optional native dependencies. Local OpenAI generation is implemented and smoke-tested; the assignment is not complete until the public site supports the same full flow.

References: [Chroma clients](https://docs.trychroma.com/docs/run-chroma/clients), [embedding functions and the default MiniLM model](https://docs.trychroma.com/docs/embeddings/embedding-functions), [vector query API](https://docs.trychroma.com/docs/querying-collections/query-and-get), [cosine index configuration](https://docs.trychroma.com/docs/collections/configure).
