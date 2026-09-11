import re

from app.config import settings


def chunk_markdown_qa(text: str) -> list[str]:
    """Split a markdown Q&A file into one chunk per top-level (#) section.

    Given:
        # Question 1
        Answer 1

        # Question 2
        Answer 2

    Returns ["Question 1\\nAnswer 1", "Question 2\\nAnswer 2"] — each
    chunk keeps its question and answer together, which is what you want
    for retrieval (you never want the answer split away from its question).

    Only single '#' headers act as split points; '##' or deeper headers
    inside an answer stay part of that answer's chunk.
    """
    normalized = text.replace("\r\n", "\n")
    # Zero-width split right before every line that starts with "# "
    # (a literal "## " won't match, since the char after '#' must be a space)
    sections = re.split(r"(?m)^(?=# )", normalized)

    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        heading, _, body = section.partition("\n")
        heading = heading.lstrip("#").strip()
        body = body.strip()
        chunks.append(f"{heading}\n{body}" if body else heading)
    return chunks


def chunk_text(text: str) -> list[str]:
    """Simple fixed-size character chunker with overlap.
    Good enough to start; swap in a token-aware or semantic chunker later
    if retrieval quality needs it."""
    size = settings.chunk_size
    overlap = settings.chunk_overlap
    text = " ".join(text.split())  # collapse whitespace/newlines

    if len(text) <= size:
        return [text] if text else []

    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks
