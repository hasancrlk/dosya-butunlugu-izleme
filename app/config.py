"""Application configuration via Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Global application settings, loaded from environment / .env file."""

    DATABASE_URL: str = "sqlite:///./fim_sentinel.db"
    HASH_CHUNK_SIZE: int = 65_536  # 64 KB
    APP_NAME: str = "FIM-Sentinel"
    APP_VERSION: str = "1.1.0"
    FOLLOW_SYMLINKS: bool = False
    LOG_LEVEL: str = "INFO"

    # Security
    API_KEY: str = ""                 # required for the REST API (X-API-Key header)
    HMAC_KEY: str = ""                # required: signs baselines and the audit chain
    ALLOWED_PATHS: list[str] = []     # API may only scan inside these dirs (JSON list)

    model_config = {"env_file": ".env", "env_prefix": "FIM_"}


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings singleton."""
    return Settings()


def get_hmac_key() -> bytes:
    """Return the HMAC key or fail loudly — integrity features must not run unkeyed."""
    key = get_settings().HMAC_KEY
    if len(key) < 32:
        raise RuntimeError("FIM_HMAC_KEY must be set (at least 32 characters).")
    return key.encode()
