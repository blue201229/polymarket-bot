"""Phase 1 Discord adapter (skeleton).

This is intentionally lightweight: no direct execution logic, only API reads.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

import httpx


@dataclass
class Config:
    api_base_url: str = os.getenv("BACKEND_API_URL", "http://localhost:8000")


class DiscordClientAdapter:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.http = httpx.AsyncClient(base_url=config.api_base_url, timeout=5.0)

    async def fetch_markets(self, with_ai: bool = True) -> dict:
        _ = with_ai
        response = await self.http.get("/api/v1/markets")
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        await self.http.aclose()


async def main() -> None:
    config = Config()
    adapter = DiscordClientAdapter(config)
    try:
        data = await adapter.fetch_markets(with_ai=True)
        markets = data.get("markets", [])
        top = markets[0] if markets else {}
        title = top.get("question", "n/a")
        score = top.get("ai_score")
        print(f"[discord] top market: {title} (ai_score={score})")
    finally:
        await adapter.close()


if __name__ == "__main__":
    asyncio.run(main())
