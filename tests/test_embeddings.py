from unittest.mock import MagicMock

import pytest
from pgvector.psycopg import Vector

from app.embeddings import EmbeddingError, embed_documents, embed_query


def _fake_embed_result(vectors):
    return MagicMock(embeddings=vectors)


def test_embed_documents_uses_document_input_type(monkeypatch):
    fake_client = MagicMock()
    fake_client.embed.return_value = _fake_embed_result([[0.1, 0.2], [0.3, 0.4]])
    monkeypatch.setattr("app.embeddings._client", fake_client)

    result = embed_documents(["a", "b"])

    assert fake_client.embed.call_args.kwargs["input_type"] == "document"
    assert all(isinstance(v, Vector) for v in result)


def test_embed_query_uses_query_input_type(monkeypatch):
    fake_client = MagicMock()
    fake_client.embed.return_value = _fake_embed_result([[0.1, 0.2]])
    monkeypatch.setattr("app.embeddings._client", fake_client)

    result = embed_query("hello")

    assert fake_client.embed.call_args.kwargs["input_type"] == "query"
    assert isinstance(result, Vector)


def test_embed_documents_wraps_client_errors(monkeypatch):
    fake_client = MagicMock()
    fake_client.embed.side_effect = RuntimeError("voyage down")
    monkeypatch.setattr("app.embeddings._client", fake_client)

    with pytest.raises(EmbeddingError):
        embed_documents(["a"])


def test_embed_query_wraps_client_errors(monkeypatch):
    fake_client = MagicMock()
    fake_client.embed.side_effect = RuntimeError("voyage down")
    monkeypatch.setattr("app.embeddings._client", fake_client)

    with pytest.raises(EmbeddingError):
        embed_query("hello")
