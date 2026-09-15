import secrets

from fastapi import Header, HTTPException

from app.config import settings


def require_api_key(x_api_key: str = Header(...)) -> None:
    """FastAPI dependency guarding the /ingest and /documents routes.

    Uses secrets.compare_digest instead of `!=` so the comparison runs in
    constant time and doesn't leak how many leading characters matched.
    """
    if not secrets.compare_digest(x_api_key, settings.ingest_api_key):
        raise HTTPException(401, "invalid API key")
