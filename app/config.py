from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # Render injects this automatically if you attach a Postgres instance
    database_url: str

    anthropic_api_key: str
    voyage_api_key: str

    # Models — check provider docs for the latest names before deploying
    claude_model: str = "claude-sonnet-4-6"
    voyage_model: str = "voyage-3"
    embedding_dim: int = 1024

    # RAG tuning
    top_k: int = 5  # chunks retrieved per query

    # Simple shared-secret auth for the ingest endpoint. No default: an
    # unset key should fail startup, not silently fall back to a guessable
    # value.
    ingest_api_key: str

    # Path (relative to repo root) to the markdown Q/A file that gets
    # auto-ingested on every startup, if it has changed.
    qa_markdown_path: str = "Titouan.md"

    # Name used in /chat's system prompt ("...about {owner}...").
    owner_name: str = "Titouan"

    # CORS allowed origins. Comma-separated in .env, e.g.
    # CORS_ORIGINS=https://example.com,https://foo.com
    # Defaults to "*" for local/dev convenience — override before real
    # deployment.
    cors_origins: list[str] = ["*"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, v):
        # pydantic-settings expects JSON for list fields by default; accept
        # a plain comma-separated string too, since that's what humans
        # write in a .env file.
        if isinstance(v, str) and not v.strip().startswith("["):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


settings = Settings()
