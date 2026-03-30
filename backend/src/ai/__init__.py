"""
AI Module — assistant layer for the Polymarket trading platform.

PRINCIPLES:
- AI is advisory only. It NEVER executes trades directly.
- All AI outputs are explainable, logged, and optional.
- Deterministic risk rules always override AI decisions.
- AI can be disabled globally via AI_ENABLED=false.

Components:
- ai_engine.py: Abstract model calls, batching, caching, timeouts
- scoring.py: Market quality scoring (0-10)
- wallet_analysis.py: Wallet behavior classification
- trade_filter.py: Signal confidence evaluation
- optimizer.py: Parameter tuning suggestions
- anomaly_detector.py: Unusual market/wallet behavior detection
- post_trade.py: Post-trade analysis and insight generation
"""
from .ai_engine import AIEngine, get_ai_engine

__all__ = ["AIEngine", "get_ai_engine"]
