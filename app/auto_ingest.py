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
import logging
import os

from app.chunking import chunk_markdown_qa
from app.config import settings
from app.db import get_conn
from app.embeddings import embed_documents

logger = logging.getLogger(__name__)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def auto_ingest_qa_file():
    path = settings.qa_markdown_path

    if not os.path.exists(path):
        logger.info("%s not found in repo, skipping", path)
        return

    with open(path, encoding="utf-8") as f:
        text = f.read()

    new_hash = _hash(text)

    with get_conn() as conn:
        row = conn.execute(
            "SELECT content_hash FROM ingested_sources WHERE source = %s",
            (path,),
        ).fetchone()

    if row and row[0] == new_hash:
        logger.info("%s unchanged since last deploy, skipping", path)
        return

    chunks = chunk_markdown_qa(text)
    logger.info("%s is new or changed — ingesting %d chunks", path, len(chunks))

    vectors = embed_documents(chunks) if chunks else []

    with get_conn() as conn, conn.cursor() as cur:
        # Replace this source's chunks entirely rather than appending,
        # so edits/deletions in the markdown are reflected correctly.
        cur.execute("DELETE FROM documents WHERE source = %s", (path,))
        if chunks:
            cur.executemany(
                "INSERT INTO documents (source, content, embedding) "
                "VALUES (%s, %s, %s)",
                [(path, c, v) for c, v in zip(chunks, vectors, strict=True)],
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

    logger.info("done — %d chunks stored for %s", len(chunks), path)
