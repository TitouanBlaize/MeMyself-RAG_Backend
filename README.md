# Personal RAG Backend

A minimal RAG API: FastAPI + Postgres/pgvector (Render) + Voyage embeddings + Claude.

## Endpoints

- `GET /health` — liveness check
- `POST /chat` — `{"question": "..."}` → retrieves relevant chunks, asks Claude, returns `{answer, sources}`
- `POST /ingest/text` — `{"source": "...", "text": "..."}` (header `x-api-key: <INGEST_API_KEY>`) → chunks, embeds, and stores text
- `DELETE /ingest/{source}` — removes all chunks for a given source (header `x-api-key: <INGEST_API_KEY>`)
- `GET /documents` — lists stored chunks (header `x-api-key: <INGEST_API_KEY>`); filter with `?source=`, page with `?limit=&offset=`
- `GET /documents/sources` — summarizes each distinct source with its chunk count and last update (header `x-api-key: <INGEST_API_KEY>`)

## Local development

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your keys and a local Postgres URL
uvicorn app.main:app --reload
```

You'll need a local Postgres with the `vector` extension available (the
easiest way is the `pgvector/pgvector` Docker image), or just point
`DATABASE_URL` at your Render database's "External Connection String"
during development.

## Deploying to Render

1. Push this repo to GitHub.
2. In Render, choose **New > Blueprint** and point it at the repo —
   `render.yaml` provisions both the web service and the Postgres
   database in one go.
3. In the service's **Environment** tab, set the secret values Render
   left blank: `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`, `INGEST_API_KEY`.
4. Deploy. Check `GET https://<your-service>.onrender.com/health`.

## Ingesting your documents

Content is ingested from a single **markdown Q/A file**, formatted like:

```markdown
# Question 1
Answer 1

# Question 2
Answer 2
```

Each top-level (`#`) heading and everything below it (up to the next `#`
heading) becomes one chunk — so a question is always stored, and
retrieved, together with its own answer. `##`/`###` headings inside an
answer are left alone and stay part of that answer's chunk.

Run the CLI script **from your own machine**, pointed at the database's
*external* connection string (find it on the database's page in the
Render dashboard — the internal one only resolves inside Render's
network):

```bash
export DATABASE_URL="<external connection string from Render>"
export VOYAGE_API_KEY="..."
python ingest.py qa.md
```

Re-running it will insert duplicate rows for unchanged questions —
either clear the source first with `DELETE /ingest/{source}` (source
will be the file path, e.g. `qa.md`) or add your own upsert logic if
you'll be editing the file repeatedly.

Or use the `/ingest/text` endpoint directly if you'd rather POST the
markdown content instead of running the script locally.

## Calling it from your frontend

```js
const res = await fetch("https://<your-service>.onrender.com/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ question: "What did Antoine study?" }),
});
const { answer, sources } = await res.json();
```

Remember to restrict `allow_origins` in `app/main.py`'s CORS middleware
to your actual frontend domain before going live — `"*"` is fine for
testing only.

## Notes & things to tune later

- **Free tier cold starts**: the free web service spins down after ~15
  min idle; first request after that takes 10–30s. Upgrade to a paid
  plan to avoid this, or ping `/health` periodically to keep it warm.
- **Chunking**: chunks are split at `#` headings in your markdown Q/A
  file, one question+answer per chunk. If some answers are very long,
  consider also enforcing a max chunk size so a single answer doesn't
  dominate the retrieved context.
- **Model names**: double-check the current Claude and Voyage model
  names/dimensions in each provider's docs before deploying — these
  change over time and `embedding_dim` in `app/config.py` must match
  whatever Voyage model you pick.
