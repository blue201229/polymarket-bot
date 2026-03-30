"""Telegram client skeleton for the shared backend.

This intentionally keeps trading logic out of the bot. It only calls backend APIs.
"""

from __future__ import annotations

import os
from typing import Any

import requests

API_BASE = os.getenv("POLYMARKET_API_BASE", "http://localhost:8000")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def fetch_top_markets() -> list[dict[str, Any]]:
    response = requests.get(f"{API_BASE}/api/v1/markets", timeout=5)
    response.raise_for_status()
    return response.json().get("markets", [])


def format_ai_summary(market: dict[str, Any]) -> str:
    ai = market.get("ai_score")
    reason = market.get("ai_reasoning", "AI disabled or unavailable.")
    title = market.get("question", market.get("title", "Unknown market"))
    if ai is None:
        return f"{title}\nAI: disabled\n{reason}"
    return f"{title}\nHigh conviction ({ai:.1f}/10)\n{reason}"


def send_message(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram env vars are not configured. Message:")
        print(text)
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    requests.post(url, json=payload, timeout=5).raise_for_status()


def main() -> None:
    markets = fetch_top_markets()
    if not markets:
        send_message("No markets available right now.")
        return
    top = markets[0]
    send_message(format_ai_summary(top))


if __name__ == "__main__":
    main()
