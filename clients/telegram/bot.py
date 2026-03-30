from __future__ import annotations

from typing import Iterable


def render_market_alert(candidates: Iterable[dict]) -> str:
    lines = ["Polymarket AI Platform - Telegram summary"]
    for candidate in candidates:
        market = candidate["market"]
        ai_score = candidate.get("ai_score")
        if ai_score:
            ai_summary = f"High conviction ({ai_score['score']:.1f}/10) - {ai_score['reasoning']}"
        else:
            ai_summary = "AI disabled - deterministic ranking only"
        lines.append(
            f"- {market['question']} | priority={candidate['priority_score']:.2f} | {ai_summary}"
        )
    return "\n".join(lines)
