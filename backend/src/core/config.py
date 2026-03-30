from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PM_", case_sensitive=False)

    app_name: str = "Polymarket AI-Assisted Trading Platform"
    app_env: str = "dev"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"

    ai_enabled: bool = True
    ai_provider: str = "mock"
    ai_model: str = "mock-v1"
    ai_timeout_seconds: float = 2.5
    ai_cache_ttl_seconds: int = 300
    ai_max_batch_size: int = 32


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
