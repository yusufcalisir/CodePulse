"""Application configuration via environment variables."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """CodePulse application settings.

    All values are loaded from environment variables or a .env file.
    """

    # ── Application ──────────────────────────────────────────
    APP_NAME: str = "CodePulse"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # ── Database ─────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://codepulse:codepulse@localhost:5432/codepulse"
    DATABASE_URL_SYNC: str = "postgresql://codepulse:codepulse@localhost:5432/codepulse"

    # ── Redis ────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── GitHub ───────────────────────────────────────────────
    GITHUB_TOKEN: str = ""
    GITHUB_GRAPHQL_URL: str = "https://api.github.com/graphql"

    # ── CORS ─────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings (singleton)."""
    return Settings()
