"""
Ingest a markdown Q/A file into the RAG database.

Expected format — one chunk per top-level heading, question + answer
kept together:

    # Question 1
    Answer 1

    # Question 2
    Answer 2

Usage:
    python ingest.py path/to/qa.md

Run this from your machine against the Render Postgres external
connection string (set DATABASE_URL to the "External" URL Render shows
you, not the internal one — the internal one only works from inside
Render's network).
"""

import logging
import os
import sys

from app.chunking import chunk_markdown_qa
from app.db import get_conn, init_db
from app.embeddings import embed_documents

logger = logging.getLogger(__name__)


def ingest_file(path: str):
    logger.info("Reading %s...", path)
    with open(path, encoding="utf-8") as f:
        text = f.read()

    chunks = chunk_markdown_qa(text)
    if not chunks:
        logger.info("no '# heading' sections found — nothing to ingest")
        return

    logger.info("%d Q/A chunks, embedding...", len(chunks))
    vectors = embed_documents(chunks)

    with get_conn() as conn, conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO documents (source, content, embedding) VALUES (%s, %s, %s)",
            [(path, c, v) for c, v in zip(chunks, vectors, strict=True)],
        )
    logger.info("inserted %d chunks from %s", len(chunks), path)


if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))

    if len(sys.argv) != 2:
        print("Usage: python ingest.py qa.md")
        sys.exit(1)

    init_db()
    ingest_file(sys.argv[1])
