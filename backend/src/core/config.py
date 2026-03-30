"""Central configuration using pydantic-settings."""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "development"
    app_secret_key: str = "change-me-in-production"
    app_debug: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Database
    database_url: str = "postgresql+asyncpg://polymarket:polymarket@localhost:5432/polymarket"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Polymarket
    polymarket_api_key: str = ""
    polymarket_api_secret: str = ""
    polymarket_api_passphrase: str = ""
    polymarket_host: str = "https://clob.polymarket.com"
    polymarket_gamma_host: str = "https://gamma-api.polymarket.com"
    polymarket_chain_id: int = 137

    # Wallet
    wallet_private_key: str = ""
    wallet_address: str = ""

    # AI - Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    anthropic_max_tokens: int = 1024
    ai_timeout_seconds: float = 3.0
    ai_cache_ttl_seconds: int = 300
    ai_enabled: bool = True

    # AI - OpenAI (fallback)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Telegram
    telegram_bot_token: str = ""
    telegram_allowed_users: str = ""

    # Discord
    discord_bot_token: str = ""
    discord_guild_id: str = ""
    discord_channel_id: str = ""

    # Trading
    paper_trading_mode: bool = True
    max_position_size_usdc: float = 100.0
    max_total_exposure_usdc: float = 1000.0
    max_positions: int = 10
    default_slippage_pct: float = 0.02
    risk_engine_enabled: bool = True

    # Monitoring
    sentry_dsn: str = ""
    prometheus_port: int = 9090

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8080"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: str) -> str:
        return v

    def get_cors_origins(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def get_telegram_allowed_users(self) -> List[int]:
        if not self.telegram_allowed_users:
            return []
        return [int(u.strip()) for u in self.telegram_allowed_users.split(",") if u.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def ai_available(self) -> bool:
        return self.ai_enabled and bool(self.anthropic_api_key or self.openai_api_key)


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
