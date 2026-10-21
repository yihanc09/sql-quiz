# Chroma Cloud retrieval

## Verified scope

The 17 curated knowledge documents have been embedded with OpenAI `text-embedding-3-small` (1536 dimensions) and indexed in Chroma Cloud. Both vector retrieval and the cloud retrieval → OpenAI SQL-generation flow passed real requests on October 21, 2026 using the HTTP-only Chroma client in a clean environment, without ONNX or local model weights.

See [real cloud retrieval](examples/chroma_cloud_retrieval.json) and [real cloud RAG generation](examples/chroma_cloud_generation.json). These are CLI verification records, not public-deployment screenshots. The local application can now use cloud retrieval; the public Vercel site still needs deployment environment configuration and the updated code.

## Backend configuration

Set these values in the ignored root `.env`. Copy the tenant, database, key and region hostname from the database's Chroma Cloud **Connect** panel:

```dotenv
CHROMA_MODE=cloud
CHROMA_API_KEY=your_chroma_cloud_api_key
CHROMA_TENANT=your_tenant_id
CHROMA_DATABASE=your_database_name
CHROMA_HOST=api.trychroma.com
CHROMA_CLOUD_COLLECTION=chinook_knowledge_openai3small_v1
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-mini
```

Use the regional hostname shown in Connect; for an EU database it may be `europe-west1.gcp.trychroma.com`. Supply a hostname without a URL scheme or path. Keys remain on the backend; the public frontend never connects directly to Chroma or OpenAI.

## Install and index

For a clean cloud-only environment:

```bash
python3.12 -m venv .venv-cloud
.venv-cloud/bin/python -m pip install -r requirements.txt
.venv-cloud/bin/python -m scripts.index_knowledge --cloud
.venv-cloud/bin/python -m scripts.check_cloud
.venv-cloud/bin/python -m scripts.search_knowledge --cloud "What is the average track duration in minutes for each genre?"
.venv-cloud/bin/python -m scripts.generate_sql --cloud "How many artists are there?"
.venv-cloud/bin/python web_server.py --port 8001
```

The existing full local `.venv` can run these cloud commands too. Indexing sends the 17 curated knowledge documents to OpenAI for embedding, then uploads documents, vectors and metadata to Chroma Cloud. It does not upload business rows, quiz answers, student submissions or audit logs. Reindexing upserts stable IDs and removes stale IDs only within this application-managed collection. The status command does not call either OpenAI API.

Do not install `chromadb` and `chromadb-client` together: they provide the same import namespace. `requirements.txt` uses the HTTP-only distribution; `requirements-rag.txt` uses full local Chroma instead. Both share `requirements-core.txt`. The existing full local environment remains usable; use a separate clean environment for cloud-only installation.

## Model consistency

| Backend | Collection | Embedding model | Dimensions |
|---|---|---|---|
| Local | `chinook_knowledge_minilm_v1` | `all-MiniLM-L6-v2` | 384 |
| Cloud | `chinook_knowledge_openai3small_v1` | `text-embedding-3-small` | 1536 |

The cloud path uses the same OpenAI embedding request for document indexing and question retrieval, with explicit dimensions. It does not mix MiniLM vectors into the cloud collection. Collection metadata verifies model identity, dimensions, ready status and corpus fingerprint before querying. Cloud uses a SPANN cosine index; local uses HNSW cosine.

`CHROMA_MODE=cloud` selects cloud retrieval. Without a mode, local development defaults to local and Vercel defaults to cloud. An explicitly requested local mode is rejected on Vercel. Cloud failures do not fall back to a local index or prompt-only generation.

To return to the preserved local index, set `CHROMA_MODE=local`, use the full local environment, and restart the server. Neither cloud indexing nor switching modes deletes `.chroma/`.

## Web workflow

Start/restart the server, sign in, and choose **Knowledge** on a question. **Search knowledge only** tests retrieval. **Generate SQL** retrieves cloud knowledge and calls OpenAI Responses. Retrieval details identify the backend, embedding model and dimensions; generated SQL retains the IDs of sources used for that generation. **Use in editor** does not execute or save SQL. Existing Run/Submit actions use the restricted database reader.

## Vercel deployment checklist

1. Add the above environment variables in the existing Vercel project's backend settings; choose production and any intended preview environments. Keep the existing database/session settings.
2. Deploy the updated Python/frontend code from the synchronized `yihanc09/sql-quiz` repository. `pyproject.toml` includes `chromadb-client` and `httpx` as runtime dependencies. No local index/model needs to be bundled or downloaded.
3. Sign in on the public site, generate SQL, inspect cloud retrieval evidence, and optionally run the generated query with the existing reader.
4. Capture the question/generated-SQL screenshot and update the submission README. Manual Run/Submit actions do not establish automatic execution/validation extra credit.

At the time of this update, steps 1–4 have not been completed for the public site. Local cloud connectivity alone does not establish successful public deployment.

## Offline verification

```bash
# Full local environment: all offline tests plus actual local Chroma tests.
.venv/bin/python -m pytest tests/unit tests/vector -q
# Cloud-only environment: unit tests, without PersistentClient/model weights.
.venv-cloud/bin/python -m pytest tests/unit -q
```

Cloud tests cover missing credentials, accepted hostnames, secret redaction, embedding response ordering/dimensions, sanitized failures and cloud selection on Vercel without fallback.

References: [Chroma clients and regional configuration](https://docs.trychroma.com/docs/run-chroma/clients), [Chroma thin client and serverless embeddings](https://docs.trychroma.com/guides/performance/general), [OpenAI embeddings](https://developers.openai.com/api/docs/guides/embeddings).
