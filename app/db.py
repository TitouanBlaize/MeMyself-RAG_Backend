from contextlib import contextmanager

import psycopg
from psycopg_pool import ConnectionPool
from pgvector.psycopg import register_vector

from app.config import settings

# Render's internal Postgres URL works fine here; the pool keeps a handful
# of connections warm so requests don't pay connection-setup cost.
pool = ConnectionPool(
    conninfo=settings.database_url,
    min_size=1,
    max_size=5,
    kwargs={"autocommit": True},
)


@contextmanager
def get_conn():
    with pool.connection() as conn:
        register_vector(conn)
        yield conn


def init_db():
    """Create the extension and table if they don't exist yet.
    Safe to call on every startup.

    IMPORTANT: register_vector() (used by get_conn) looks up the 'vector'
    type's OID in pg_type, so it fails on a brand-new database where the
    extension hasn't been created yet. We create the extension first on a
    raw connection, then switch to get_conn() for everything else.
    """
    with pool.connection() as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

    with get_conn() as conn:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS documents (
                id BIGSERIAL PRIMARY KEY,
                source TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding VECTOR({settings.embedding_dim}) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now()
            )
            """
        )
        # IVFFlat index speeds up similarity search once you have a
        # meaningful number of rows (a few hundred+). Harmless before that.
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS documents_embedding_idx
            ON documents USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
            """
        )
