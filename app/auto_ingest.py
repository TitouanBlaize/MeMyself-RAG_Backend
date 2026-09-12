"""
Automatically ingests app.config.settings.qa_markdown_path (e.g. Titouan.md)
on every app startup. Because Render rebuilds and restarts your service on
every deploy, this means: commit Titouan.md, push, and the database updates
itself — no manual ingest.py step needed.

To avoid re-embedding (and re-paying for) unchanged content on every
restart, we store a hash of the file's content in `ingested_sources` and
only re-ingest when that hash changes.
"""
import hashlib
import os

from app.chunking import chunk_markdown_qa
from app.config import settings
from app.db import get_conn
from app.embeddings import embed_documents


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def auto_ingest_qa_file():
    path = settings.qa_markdown_path

    if not os.path.exists(path):
        print(f"[auto_ingest] {path} not found in repo, skipping")
        return

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    new_hash = _hash(text)

    with get_conn() as conn:
        row = conn.execute(
            "SELECT content_hash FROM ingested_sources WHERE source = %s",
            (path,),
        ).fetchone()

    if row and row[0] == new_hash:
        print(f"[auto_ingest] {path} unchanged since last deploy, skipping")
        return

    chunks = chunk_markdown_qa(text)
    print(f"[auto_ingest] {path} is new or changed — ingesting {len(chunks)} chunks")

    vectors = embed_documents(chunks) if chunks else []

    with get_conn() as conn, conn.cursor() as cur:
        # Replace this source's chunks entirely rather than appending,
        # so edits/deletions in the markdown are reflected correctly.
        cur.execute("DELETE FROM documents WHERE source = %s", (path,))
        if chunks:
            cur.executemany(
                "INSERT INTO documents (source, content, embedding) VALUES (%s, %s, %s)",
                [(path, c, v) for c, v in zip(chunks, vectors)],
            )
        cur.execute(
            """
            INSERT INTO ingested_sources (source, content_hash, updated_at)
            VALUES (%s, %s, now())
            ON CONFLICT (source)
            DO UPDATE SET content_hash = EXCLUDED.content_hash, updated_at = now()
            """,
            (path, new_hash),
        )

    print(f"[auto_ingest] done — {len(chunks)} chunks stored for {path}")
