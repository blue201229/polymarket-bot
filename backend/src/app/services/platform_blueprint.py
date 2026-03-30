from app.domain.models import BlueprintResponse, PhaseDefinition


class PlatformBlueprintService:
    def get_blueprint(self) -> dict:
        blueprint = BlueprintResponse(
            backend={
                "shape": "shared service",
                "modules": [
                    "market discovery",
                    "execution",
                    "risk",
                    "paper trading",
                    "wallet watcher",
                    "arbitrage jobs",
                    "ai engine",
                ],
                "authoritative_layers": ["risk engine", "execution rules", "auth"],
            },
            frontends=[
                {"name": "telegram", "role": "alerts and command workflows"},
                {"name": "discord", "role": "desk and community workflows"},
                {"name": "web", "role": "operator dashboard and explainability"},
                {"name": "mobile", "role": "compact monitoring and alerts"},
            ],
            ai_principles=[
                "AI is advisory and explainable.",
                "Risk and execution remain deterministic.",
                "AI outputs are logged, cached, timeout-bounded, and optional.",
                "AI may score, rank, filter, and suggest, but never bypass hard rules.",
            ],
            phases=[
                PhaseDefinition(
                    name="Phase 1",
                    scope=["backend foundation", "market discovery scaffold", "client contracts"],
                    ai_usage=["AI module scaffold", "market scoring interface"],
                ),
                PhaseDefinition(
                    name="Phase 2",
                    scope=["live data", "execution engine", "risk engine", "paper trading"],
                    ai_usage=["basic market scoring integration"],
                ),
                PhaseDefinition(
                    name="Phase 3",
                    scope=["wallet watcher", "copy trading"],
                    ai_usage=["wallet behavior analysis"],
                ),
                PhaseDefinition(
                    name="Phase 4",
                    scope=["arbitrage jobs", "crypto bots", "risk monitoring"],
                    ai_usage=["trade filtering", "anomaly detection"],
                ),
                PhaseDefinition(
                    name="Phase 5",
                    scope=["parameter optimization", "ui explainability", "performance tuning"],
                    ai_usage=["adaptive suggestions", "post-trade analysis"],
                ),
            ],
        )
        return blueprint.model_dump()
