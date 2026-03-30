from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration. Secrets via environment only."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    polymarket_gamma_base_url: str = Field(
        default="https://gamma-api.polymarket.com",
        description="Polymarket Gamma API base URL (public market metadata).",
    )

    ai_enabled: bool = Field(default=False, description="Master switch for AI assistant features.")
    ai_provider: str = Field(default="anthropic", description="anthropic | openai | local")
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    ai_request_timeout_seconds: float = Field(default=2.5, ge=0.5, le=10.0)
    ai_cache_ttl_seconds: int = Field(default=300, ge=0)


def get_settings() -> Settings:
    return Settings()
