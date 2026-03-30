from __future__ import annotations

from typing import Iterable


def render_market_embed_lines(candidates: Iterable[dict]) -> list[str]:
    lines: list[str] = []
    for candidate in candidates:
        market = candidate["market"]
        ai_score = candidate.get("ai_score")
        summary = ai_score["reasoning"] if ai_score else "AI disabled"
        lines.append(
            f"{market['question']} | priority {candidate['priority_score']:.2f} | {summary}"
        )
    return lines
