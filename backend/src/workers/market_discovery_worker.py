"""
Market discovery worker — scheduled job that runs discovery + scoring cycles.
Can be run standalone (via celery beat) or embedded in the FastAPI app.
"""
import asyncio

from src.core.config import settings
from src.core.logging import get_logger
from src.services.market_service import MarketService

logger = get_logger(__name__)


async def run_discovery_cycle(
    limit: int = 200,
    min_volume: float = 500,
) -> None:
    """Single discovery + scoring cycle."""
    service = MarketService()
    result = await service.discover_and_score_markets(
        limit=limit,
        min_volume=min_volume,
        score_with_ai=settings.ai_available,
    )
    logger.info("discovery_cycle_complete", **result)


async def run_continuous(interval_seconds: int = 600) -> None:
    """Run discovery cycles continuously."""
    logger.info("market_discovery_worker_starting", interval=interval_seconds)
    while True:
        try:
            await run_discovery_cycle()
        except Exception as e:
            logger.error("discovery_cycle_failed", error=str(e))
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    asyncio.run(run_continuous())
