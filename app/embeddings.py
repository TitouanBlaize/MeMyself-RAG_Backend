import voyageai

from app.config import settings

_client = voyageai.Client(api_key=settings.voyage_api_key)


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed chunks that will be stored (input_type='document' improves
    retrieval quality vs. a generic embed call)."""
    result = _client.embed(
        texts,
        model=settings.voyage_model,
        input_type="document",
    )
    return result.embeddings


def embed_query(text: str) -> list[float]:
    result = _client.embed(
        [text],
        model=settings.voyage_model,
        input_type="query",
    )
    return result.embeddings[0]
