"""Domain exceptions for the platform."""
from typing import Any, Dict, Optional


class PlatformError(Exception):
    """Base class for all platform errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class RiskEngineError(PlatformError):
    """Raised when a trade violates risk rules. Never bypassed by AI."""
    pass


class ExecutionError(PlatformError):
    """Trade execution failure."""
    pass


class MarketNotFoundError(PlatformError):
    pass


class InsufficientLiquidityError(PlatformError):
    pass


class SlippageExceededError(PlatformError):
    pass


class AIError(PlatformError):
    """AI call failure — should trigger fallback behavior, never halt execution."""
    pass


class AITimeoutError(AIError):
    """AI call timed out."""
    pass


class ConfigurationError(PlatformError):
    pass


class WalletError(PlatformError):
    pass
