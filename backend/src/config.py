from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Environment = Environment.DEVELOPMENT
    log_level: str = "INFO"

    # Database
    database_url: str = "sqlite+aiosqlite:///./polymarket_platform.db"
    database_url_sqlite: str = "sqlite+aiosqlite:///./polymarket_platform.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Polymarket
    polymarket_api_url: str = "https://clob.polymarket.com"
    polymarket_ws_url: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    polymarket_gamma_url: str = "https://gamma-api.polymarket.com"
    polymarket_private_key: str = ""
    polymarket_api_key: str = ""
    polymarket_api_secret: str = ""
    polymarket_api_passphrase: str = ""

    # AI
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ai_default_provider: str = "anthropic"
    ai_default_model: str = "claude-sonnet-4-20250514"
    ai_timeout_seconds: float = 3.0
    ai_enabled: bool = True
    ai_cache_ttl_seconds: int = 300

    # Telegram
    telegram_bot_token: str = ""
    telegram_allowed_users: str = ""

    # Discord
    discord_bot_token: str = ""
    discord_guild_id: str = ""

    # Trading
    paper_trading: bool = True
    max_position_size_usd: float = 100.0
    max_daily_loss_usd: float = 50.0
    max_open_positions: int = 10
    default_slippage_bps: int = 50

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def db_url(self) -> str:
        if self.database_url.startswith("postgresql"):
            return self.database_url
        return self.database_url_sqlite


settings = Settings()
