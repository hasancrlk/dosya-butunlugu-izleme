"""Application configuration via Pydantic Settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Global application settings, loaded from environment / .env file."""

    DATABASE_URL: str = "sqlite:///./fim_sentinel.db"
    HASH_CHUNK_SIZE: int = 65_536  # 64 KB
    APP_NAME: str = "FIM-Sentinel"
    APP_VERSION: str = "1.0.0"
    FOLLOW_SYMLINKS: bool = False
    LOG_LEVEL: str = "INFO"

    model_config = {"env_file": ".env", "env_prefix": "FIM_"}


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings singleton."""
    return Settings()
