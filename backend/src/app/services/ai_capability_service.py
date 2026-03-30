from functools import lru_cache

from app.domain.models import CapabilityDescriptor


class AICapabilityService:
    def list_capabilities(self) -> dict:
        capabilities = [
            CapabilityDescriptor(
                capability="market_scoring",
                status="implemented",
                deterministic_owner="market discovery filters",
                ai_role="Scores and explains hard-filtered markets.",
            ),
            CapabilityDescriptor(
                capability="wallet_behavior_analysis",
                status="scaffolded",
                deterministic_owner="copy-trading rules",
                ai_role="Classifies wallet style and confidence.",
            ),
            CapabilityDescriptor(
                capability="trade_signal_filtering",
                status="scaffolded",
                deterministic_owner="strategy and risk gates",
                ai_role="Ranks trade candidates and suggests size modifiers.",
            ),
            CapabilityDescriptor(
                capability="parameter_optimization",
                status="scaffolded",
                deterministic_owner="human validation workflow",
                ai_role="Suggests parameter adjustments with rationale.",
            ),
            CapabilityDescriptor(
                capability="anomaly_detection",
                status="scaffolded",
                deterministic_owner="risk controls",
                ai_role="Flags unusual market or wallet behavior.",
            ),
            CapabilityDescriptor(
                capability="post_trade_analysis",
                status="scaffolded",
                deterministic_owner="operator review",
                ai_role="Summarizes why a trade succeeded or failed.",
            ),
        ]
        return {"capabilities": [item.model_dump() for item in capabilities]}


@lru_cache(maxsize=1)
def get_ai_capability_service() -> AICapabilityService:
    return AICapabilityService()
