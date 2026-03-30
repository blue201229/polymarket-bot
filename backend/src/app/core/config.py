from dataclasses import dataclass
from functools import lru_cache
import os


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    service_name: str = os.getenv("SERVICE_NAME", "polymarket-ai-platform-backend")
    api_prefix: str = os.getenv("API_PREFIX", "/api/v1")
    ai_enabled: bool = _as_bool(os.getenv("AI_ENABLED"), True)
    ai_provider: str = os.getenv("AI_PROVIDER", "mock")
    ai_timeout_seconds: float = float(os.getenv("AI_TIMEOUT_SECONDS", "2.5"))
    ai_cache_ttl_seconds: int = int(os.getenv("AI_CACHE_TTL_SECONDS", "300"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
