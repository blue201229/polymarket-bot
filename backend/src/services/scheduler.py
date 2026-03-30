from __future__ import annotations

import asyncio
from typing import Any, Optional

from backend.src.core.logging import get_logger
from backend.src.services.market_discovery import MarketDiscoveryService
from backend.src.services.anomaly_monitor import AnomalyMonitor

logger = get_logger("services.scheduler")


class JobScheduler:
    """
    Manages periodic background jobs:

    - Market discovery (fetch and score new markets)
    - Anomaly monitoring (check active positions for risks)
    - Wallet polling (detect new transactions)
    - Position updates (refresh prices)
    - AI re-scoring (periodic re-evaluation of markets)
    - Performance reporting
    """

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._running = False
        self._tasks: list[asyncio.Task] = []

    def register_job(
        self,
        name: str,
        coroutine: Any,
        interval_seconds: int,
        enabled: bool = True,
    ) -> None:
        self._jobs[name] = {
            "coroutine": coroutine,
            "interval": interval_seconds,
            "enabled": enabled,
            "run_count": 0,
            "last_error": None,
        }
        logger.info("Job registered", name=name, interval=interval_seconds)

    async def start(self) -> None:
        self._running = True
        logger.info("Scheduler starting", jobs=len(self._jobs))

        for name, job in self._jobs.items():
            if job["enabled"]:
                task = asyncio.create_task(self._run_job(name, job))
                self._tasks.append(task)

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("Scheduler stopped")

    async def _run_job(self, name: str, job: dict[str, Any]) -> None:
        while self._running:
            try:
                await job["coroutine"]()
                job["run_count"] += 1
                job["last_error"] = None
            except asyncio.CancelledError:
                break
            except Exception as e:
                job["last_error"] = str(e)
                logger.error("Job failed", name=name, error=str(e))

            await asyncio.sleep(job["interval"])

    def get_status(self) -> dict[str, Any]:
        return {
            name: {
                "enabled": job["enabled"],
                "interval": job["interval"],
                "run_count": job["run_count"],
                "last_error": job["last_error"],
            }
            for name, job in self._jobs.items()
        }


def create_default_scheduler(
    discovery: MarketDiscoveryService,
    anomaly_monitor: AnomalyMonitor,
) -> JobScheduler:
    scheduler = JobScheduler()

    scheduler.register_job(
        name="market_discovery",
        coroutine=lambda: discovery.discover_markets(limit=50, with_ai_scoring=True),
        interval_seconds=300,
    )

    scheduler.register_job(
        name="anomaly_check",
        coroutine=anomaly_monitor._check_all_markets,
        interval_seconds=60,
    )

    return scheduler
