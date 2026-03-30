"""Structured logging configuration."""
import logging
import sys
from typing import Any, Dict

import structlog

from .config import settings


def configure_logging() -> None:
    log_level = logging.DEBUG if settings.app_debug else logging.INFO

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
    ]

    if settings.app_debug:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)


class AIDecisionLogger:
    """Dedicated logger for AI decisions — every AI output must go through this."""

    def __init__(self):
        self._log = get_logger("ai.decisions")

    def log(
        self,
        *,
        component: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        latency_ms: float,
        model: str,
        cache_hit: bool = False,
        decision_impact: str = "none",
    ) -> None:
        self._log.info(
            "ai_decision",
            component=component,
            input_summary=self._summarize(input_data),
            output=output_data,
            latency_ms=round(latency_ms, 2),
            model=model,
            cache_hit=cache_hit,
            decision_impact=decision_impact,
        )

    def _summarize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Truncate large fields for log readability."""
        summary = {}
        for k, v in data.items():
            if isinstance(v, str) and len(v) > 200:
                summary[k] = v[:200] + "..."
            elif isinstance(v, (list, dict)) and len(str(v)) > 500:
                summary[k] = f"[truncated, len={len(v)}]"
            else:
                summary[k] = v
        return summary


ai_decision_logger = AIDecisionLogger()
