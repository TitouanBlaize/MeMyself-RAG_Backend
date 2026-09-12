from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.auto_ingest import auto_ingest_qa_file
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
    auto_ingest_qa_file()


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

    with get_conn() as conn, conn.cursor() as cur:
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


class ChunkOut(BaseModel):
    id: int
    source: str
    content: str
    created_at: str


@app.get("/documents", response_model=list[ChunkOut])
def list_documents(
    x_api_key: str = Header(...),
    source: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    """Lists stored chunks, most recent last. Filter with ?source=Titouan.md
    and page through results with ?limit=&offset=."""
    if x_api_key != settings.ingest_api_key:
        raise HTTPException(401, "invalid API key")

    limit = max(1, min(limit, 500))  # guard against accidentally huge pulls
    offset = max(0, offset)

    query = "SELECT id, source, content, created_at FROM documents"
    params: list = []
    if source:
        query += " WHERE source = %s"
        params.append(source)
    query += " ORDER BY id LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()

    return [
        {
            "id": r[0],
            "source": r[1],
            "content": r[2],
            "created_at": r[3].isoformat(),
        }
        for r in rows
    ]


@app.get("/documents/sources")
def list_sources(x_api_key: str = Header(...)):
    """Summarizes what's in the database: each distinct source and how
    many chunks it currently has."""
    if x_api_key != settings.ingest_api_key:
        raise HTTPException(401, "invalid API key")

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT source, COUNT(*) AS chunk_count, MAX(created_at) AS last_updated
            FROM documents
            GROUP BY source
            ORDER BY source
            """
        ).fetchall()

    return [
        {"source": r[0], "chunk_count": r[1], "last_updated": r[2].isoformat()}
        for r in rows
    ]
