import json
import logging
import time
from typing import Any


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def log_ai_event(logger: logging.Logger, event: str, payload: dict[str, Any]) -> None:
    logger.info("[ai-event] %s %s", event, json.dumps(payload, default=str))


class Timer:
    def __init__(self) -> None:
        self._start = time.perf_counter()

    @property
    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000.0


def configure_logging() -> None:
    """Backward-compatible alias used by app startup."""
    setup_logging()
