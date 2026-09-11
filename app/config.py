from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Render injects this automatically if you attach a Postgres instance
    database_url: str

    anthropic_api_key: str
    voyage_api_key: str

    # Models — check provider docs for the latest names before deploying
    claude_model: str = "claude-sonnet-4-6"
    voyage_model: str = "voyage-3"
    embedding_dim: int = 1024

    # RAG tuning
    chunk_size: int = 800          # characters per chunk
    chunk_overlap: int = 150
    top_k: int = 5                 # chunks retrieved per query

    # Simple shared-secret auth for the ingest endpoint
    ingest_api_key: str = "change-me"

    class Config:
        env_file = ".env"


settings = Settings()
