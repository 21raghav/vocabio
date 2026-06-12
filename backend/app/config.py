"""Application settings, loaded from environment variables (or a .env file)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Origins permitted by CORS — the frontend dev server during development.
    cors_origins: str = "http://localhost:5173"
    # How long a fetched dictionary definition stays valid before we refetch it.
    cache_ttl_seconds: int = 86_400  # 24 hours
    # SQLite locally by default; override with a Postgres URL in Docker (Phase 4).
    database_url: str = "sqlite:///./vocabio.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
