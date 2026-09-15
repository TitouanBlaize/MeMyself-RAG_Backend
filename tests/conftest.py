# Required settings have no defaults (see app/config.py), so they must be
# set before anything imports app.config — which happens transitively the
# moment app.main (or any app.* module) is imported below.
import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test")
os.environ.setdefault("VOYAGE_API_KEY", "pa-test")
os.environ.setdefault("INGEST_API_KEY", "test-ingest-key")

from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.deps import require_api_key
from app.main import app


@pytest.fixture
def client():
    """Unauthenticated TestClient. Deliberately not used as a `with`
    context manager: entering one runs the app's lifespan (init_db() +
    auto_ingest_qa_file()), which needs a real Postgres — tests mock
    everything external instead, so lifespan must never actually run.

    raise_server_exceptions=False so an unhandled exception in a route
    comes back as the real HTTP response our global handler produces
    (what an actual client would see), instead of re-raising into the
    test — Starlette's ServerErrorMiddleware re-raises after handling by
    design, for server-side logging, which TestClient mirrors unless told
    not to.
    """
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def authed_client():
    """TestClient with the x-api-key dependency overridden to a no-op, for
    testing protected routes without a real INGEST_API_KEY check."""
    app.dependency_overrides[require_api_key] = lambda: None
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.pop(require_api_key, None)


@pytest.fixture
def fake_conn():
    """Stand-in for a psycopg connection. MagicMock auto-implements magic
    methods, so `conn.cursor()` used as `with conn.cursor() as cur:` and
    `conn.execute(...).fetchall()` work without extra setup."""
    return MagicMock()


@pytest.fixture
def make_get_conn():
    """Factory for a no-arg context-manager function matching app.db's
    get_conn() signature, so it can replace `get_conn` in app.main / app.rag
    via monkeypatch and yield a fake connection instead of a real one."""

    def _make(conn):
        @contextmanager
        def _get_conn():
            yield conn

        return _get_conn

    return _make
