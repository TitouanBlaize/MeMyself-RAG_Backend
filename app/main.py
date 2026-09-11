from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.chunking import chunk_markdown_qa
from app.config import settings
from app.db import get_conn, init_db
from app.embeddings import embed_documents
from app.rag import answer_question

app = FastAPI(title="Personal RAG API")

# Lock this down to your actual frontend domain(s) before going live.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.question.strip():
        raise HTTPException(400, "question must not be empty")
    return answer_question(req.question)


class IngestTextRequest(BaseModel):
    source: str
    text: str  # markdown, one "# Question" heading per Q/A pair


@app.post("/ingest/text")
def ingest_text(req: IngestTextRequest, x_api_key: str = Header(...)):
    """Ingests a markdown Q/A document. Each top-level (#) heading and the
    text below it (until the next # heading) becomes one chunk, so a
    question and its answer are always stored — and retrieved — together."""
    if x_api_key != settings.ingest_api_key:
        raise HTTPException(401, "invalid API key")

    chunks = chunk_markdown_qa(req.text)
    if not chunks:
        return {"chunks_ingested": 0}

    vectors = embed_documents(chunks)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO documents (source, content, embedding) VALUES (%s, %s, %s)",
                [(req.source, c, v) for c, v in zip(chunks, vectors)],
            )

    return {"chunks_ingested": len(chunks)}


@app.delete("/ingest/{source}")
def delete_source(source: str, x_api_key: str = Header(...)):
    if x_api_key != settings.ingest_api_key:
        raise HTTPException(401, "invalid API key")

    with get_conn() as conn:
        result = conn.execute("DELETE FROM documents WHERE source = %s", (source,))
        deleted = result.rowcount

    return {"deleted": deleted}
