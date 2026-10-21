# Local RAG SQL generation with OpenAI

## Current scope

The local web application performs the full question → Chroma vector retrieval → OpenAI → generated SQL flow. OpenAI was selected for this project. The backend calls the Responses API with `gpt-4.1-mini` by default; `OPENAI_MODEL` can select another model available to the account.

A real local call on October 21, 2026 retrieved five knowledge documents and generated `SELECT COUNT(*) AS total_artists FROM public.artist;`. The [captured response](examples/openai_generation.json) includes the generated SQL and actual retrieval evidence. It is a CLI smoke check, not a screenshot or a public deployment check.

Cloud retrieval has subsequently been implemented and verified; see [Chroma Cloud](CHROMA_CLOUD.md). Public RAG deployment and submission screenshots remain outstanding. The public Vercel site still runs the previously published quiz.

## Configure and run

1. Follow [local Chroma setup](CHROMA_LOCAL.md) to install `requirements-rag.txt` and build the persistent index.
2. Add these backend settings to the ignored root `.env`:

   ```dotenv
   OPENAI_API_KEY=your_own_api_key
   OPENAI_MODEL=gpt-4.1-mini
   ```

3. Check configuration without spending API tokens:

   ```bash
   .venv/bin/python -m scripts.generate_sql --check-config
   ```

4. Start or restart the local server:

   ```bash
   .venv/bin/python web_server.py --port 8001
   ```

5. Open [localhost:8001](http://localhost:8001), sign in, and open a quiz question. Choose **Knowledge**, enter the natural-language question, and click **Generate SQL**.
6. Review the generated code and expandable retrieval sources. **Use in editor** replaces the current draft without running or saving it. **Run query** uses the existing restricted PostgreSQL reader. **Submit answer** compares against the selected quiz question and saves its grade; use it only when your natural-language question matches that quiz question.

A server restart clears local login sessions; sign in again with your existing account. Saving `.env` alone does not update an already-loaded process configuration. Never commit `.env` or put an API key in browser JavaScript. API use requires an account/key with access and available quota; a ChatGPT subscription does not configure the application API key.

CLI alternative (one model call per command):

```bash
.venv/bin/python -m scripts.generate_sql "How many artists are in the Chinook database? Return one column named total_artists."
```

## Architecture

```text
Authenticated POST /api/generate {question, top_k}
  → validate natural-language input
  → MiniLM embeds the question into 384 dimensions
  → Chroma queries the persistent cosine index
  → selected knowledge text + IDs + sources, together with the question
  → OpenAI POST /v1/responses
  → SQL + model ID + retrieval evidence returned to the browser
  → explicit Use in editor → optional Run query / Submit answer
```

The request does not read the five instructor SQL answers, expected results, user submissions, audit records, or business rows. The 17-document corpus contains schema, business semantics, and two separate few-shot examples. There is no prompt-only fallback: failed/empty retrieval prevents the model call.

Only the backend receives `OPENAI_API_KEY`. The OpenAI endpoint is fixed to `https://api.openai.com/v1/responses`; requests use `store: false`, a 1200-token output cap, bounded network timeouts, and no automatic retries. Errors are translated into messages that exclude raw provider responses or credentials.

The response parser handles text after other output items, code fences, refusals, and incomplete output. Its SELECT/WITH check is a presentation check, not a SQL security boundary or correctness guarantee. Generated code is not executed automatically. Execution remains in the existing reader role with a read-only transaction, prepared single statement, 10-second timeout, and 500-row limit.

## Verification

```bash
.venv/bin/python -m pytest tests/unit tests/vector -q
```

Tests cover retrieval before generation, no model call on failed/empty retrieval, backend-only credentials, the Responses request, incomplete/refused responses, sanitized errors, login enforcement, and no SQL execution during generation. They mock the AI transport and do not consume account credits. The separate captured response above used real Chroma and OpenAI.

## Remaining deployment work

The implemented Chroma Cloud path uses OpenAI embeddings consistently for ingestion and queries; follow the cloud setup guide. Configure `OPENAI_API_KEY` and `OPENAI_MODEL` as backend deployment environment variables, then verify the full public flow. Capture the actual question/generated-SQL screen for the README. Manual run/submit buttons are useful verification tools; this stage does not claim the assignment's automatic execution/validation extra credit.

Official references: [OpenAI text generation and Responses output](https://developers.openai.com/api/docs/guides/text), [GPT-4.1 mini model](https://developers.openai.com/api/docs/models/gpt-4.1-mini).
