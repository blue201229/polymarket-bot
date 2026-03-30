"""
AI assistant layer: scoring, filtering, and suggestions only.
Deterministic risk and execution logic live outside this package and always take precedence.
"""

from ai.ai_engine import AIEngine, get_ai_engine

__all__ = ["AIEngine", "get_ai_engine"]
