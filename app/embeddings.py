import voyageai
from pgvector.psycopg import Vector

from app.config import settings

_client = voyageai.Client(api_key=settings.voyage_api_key)


def embed_documents(texts: list[str]) -> list[Vector]:
    """Embed chunks that will be stored (input_type='document' improves
    retrieval quality vs. a generic embed call).

    Wrapped in pgvector's Vector type: register_vector() only knows how
    to dump Vector/ndarray, not plain Python lists, so passing a raw list
    as a query parameter gets sent as a Postgres double precision[]
    array instead of a vector — which the <=> operator rejects.
    """
    result = _client.embed(
        texts,
        model=settings.voyage_model,
        input_type="document",
    )
    return [Vector(e) for e in result.embeddings]


def embed_query(text: str) -> Vector:
    result = _client.embed(
        [text],
        model=settings.voyage_model,
        input_type="query",
    )
    return Vector(result.embeddings[0])
