from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

from backend.src.config import settings
from backend.src.core.logging import get_logger

logger = get_logger("bots.telegram")

# Conditionally import telegram library
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application,
        CommandHandler,
        CallbackQueryHandler,
        ContextTypes,
    )
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False


class TelegramBot:
    """
    Telegram bot frontend for the Polymarket AI Trading Platform.

    Commands:
    /start - Welcome + overview
    /markets - Top AI-scored markets
    /positions - Open positions
    /trades - Recent trades
    /performance - Performance summary
    /wallets - Watched wallets
    /alerts - Recent alerts
    /ai_score <market_id> - Get AI score for a market
    /optimize - Run AI parameter optimization
    /status - System health
    """

    def __init__(self) -> None:
        self._app: Optional[Any] = None
        self._api_base = "http://localhost:8000/api/v1"

    async def start(self) -> None:
        if not HAS_TELEGRAM:
            logger.error("python-telegram-bot not installed")
            return

        token = settings.telegram_bot_token
        if not token:
            logger.error("TELEGRAM_BOT_TOKEN not set")
            return

        self._app = Application.builder().token(token).build()

        self._app.add_handler(CommandHandler("start", self._cmd_start))
        self._app.add_handler(CommandHandler("markets", self._cmd_markets))
        self._app.add_handler(CommandHandler("positions", self._cmd_positions))
        self._app.add_handler(CommandHandler("trades", self._cmd_trades))
        self._app.add_handler(CommandHandler("performance", self._cmd_performance))
        self._app.add_handler(CommandHandler("wallets", self._cmd_wallets))
        self._app.add_handler(CommandHandler("alerts", self._cmd_alerts))
        self._app.add_handler(CommandHandler("optimize", self._cmd_optimize))
        self._app.add_handler(CommandHandler("status", self._cmd_status))
        self._app.add_handler(CallbackQueryHandler(self._handle_callback))

        logger.info("Telegram bot starting")
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling()

    async def stop(self) -> None:
        if self._app:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()

    async def send_alert(self, chat_id: int, message: str) -> None:
        if self._app:
            await self._app.bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = (
            "<b>Polymarket AI Trading Platform</b>\n\n"
            "Commands:\n"
            "/markets - Top AI-scored markets\n"
            "/positions - Open positions\n"
            "/trades - Recent trades\n"
            "/performance - Performance summary\n"
            "/wallets - Watched wallets\n"
            "/alerts - Recent alerts\n"
            "/optimize - AI parameter suggestions\n"
            "/status - System health"
        )
        await update.message.reply_text(text, parse_mode="HTML")

    async def _cmd_markets(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self._api_base}/markets", params={"limit": 10})
            data = resp.json()

        markets = data.get("markets", [])
        if not markets:
            await update.message.reply_text("No markets found.")
            return

        lines = ["<b>Top Markets by AI Score</b>\n"]
        for i, m in enumerate(markets, 1):
            score = m.get("ai_score")
            score_str = f"{score:.1f}/10" if score else "N/A"
            tags = ", ".join(m.get("ai_tags", [])[:3])
            lines.append(
                f"{i}. <b>{m['question'][:60]}</b>\n"
                f"   AI: {score_str} | Vol: ${m.get('volume_24h', 0):,.0f}\n"
                f"   {tags}"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    async def _cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self._api_base}/positions")
            data = resp.json()

        positions = data.get("positions", [])
        if not positions:
            await update.message.reply_text("No open positions.")
            return

        lines = [
            f"<b>Open Positions ({data.get('open_count', 0)})</b>\n"
            f"Unrealized PnL: ${data.get('total_unrealized_pnl', 0):,.2f}\n"
        ]
        for p in positions[:10]:
            pnl = p.get("unrealized_pnl", 0)
            emoji = "+" if pnl >= 0 else ""
            lines.append(
                f"• {p['outcome'][:30]} ({p['strategy']})\n"
                f"  Entry: {p['avg_entry_price']:.3f} → {p['current_price']:.3f}\n"
                f"  PnL: {emoji}${pnl:.2f}"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    async def _cmd_trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self._api_base}/trades", params={"limit": 10})
            data = resp.json()

        trades = data.get("trades", [])
        if not trades:
            await update.message.reply_text("No recent trades.")
            return

        lines = ["<b>Recent Trades</b>\n"]
        for t in trades[:10]:
            ai_conf = t.get("ai_confidence")
            ai_str = f" | AI: {ai_conf:.1f}" if ai_conf else ""
            status_emoji = {"filled": "✓", "paper": "📝", "cancelled": "✗"}.get(
                t["status"], "?"
            )
            lines.append(
                f"{status_emoji} {t['side'].upper()} {t['outcome'][:25]} "
                f"@ {t['price']:.3f}{ai_str}\n"
                f"   ${t['size']:.2f} | {t['strategy']}"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    async def _cmd_performance(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self._api_base}/performance/summary", params={"days": 7})
            data = resp.json()

        pnl = data.get("net_pnl", 0)
        pnl_emoji = "📈" if pnl >= 0 else "📉"

        text = (
            f"<b>{pnl_emoji} Performance (7 days)</b>\n\n"
            f"Trades: {data.get('total_trades', 0)}\n"
            f"Win Rate: {data.get('win_rate', 0):.1f}%\n"
            f"Net PnL: ${pnl:,.2f}\n"
            f"Best: ${data.get('best_trade', 0):,.2f}\n"
            f"Worst: ${data.get('worst_trade', 0):,.2f}\n"
            f"Max Drawdown: ${data.get('max_drawdown', 0):,.2f}"
        )
        await update.message.reply_text(text, parse_mode="HTML")

    async def _cmd_wallets(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self._api_base}/wallets")
            data = resp.json()

        wallets = data.get("wallets", [])
        if not wallets:
            await update.message.reply_text("No watched wallets.")
            return

        lines = ["<b>Watched Wallets</b>\n"]
        for w in wallets:
            quality = w.get("ai_quality_score")
            quality_str = f"{quality:.1f}/10" if quality else "unscored"
            copy_str = "📋 COPY" if w.get("copy_enabled") else ""
            lines.append(
                f"• {w.get('label', w['address'][:10])}\n"
                f"  Quality: {quality_str} | {w.get('ai_strategy_class', '?')} {copy_str}"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    async def _cmd_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._api_base}/alerts",
                params={"limit": 10, "unacknowledged_only": True},
            )
            data = resp.json()

        alerts = data.get("alerts", [])
        if not alerts:
            await update.message.reply_text("No unacknowledged alerts.")
            return

        severity_emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}
        lines = ["<b>Alerts</b>\n"]
        for a in alerts:
            emoji = severity_emoji.get(a["severity"], "❓")
            lines.append(f"{emoji} <b>{a['title']}</b>\n   {a['message'][:100]}")

        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    async def _cmd_optimize(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Running AI optimization...")

        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{self._api_base}/ai/optimize", params={"days": 7})
            data = resp.json()

        suggestions = data.get("suggestions", [])
        if not suggestions:
            await update.message.reply_text("No parameter changes suggested.")
            return

        lines = [
            f"<b>AI Optimization Suggestions</b>\n"
            f"Confidence: {data.get('confidence', 0):.0%}\n"
        ]
        for s in suggestions:
            lines.append(
                f"• <b>{s['parameter']}</b>: {s['current_value']} → {s['suggested_value']}\n"
                f"  {s['reasoning'][:80]}"
            )
        lines.append(f"\n{data.get('overall_assessment', '')[:200]}")

        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self._api_base}/system/health")
            data = resp.json()

        text = (
            f"<b>System Status</b>\n\n"
            f"Status: {data.get('status', 'unknown')}\n"
            f"Environment: {data.get('environment', '?')}\n"
            f"Paper Trading: {'Yes' if data.get('paper_trading') else 'No'}\n"
            f"AI Enabled: {'Yes' if data.get('ai_enabled') else 'No'}"
        )
        await update.message.reply_text(text, parse_mode="HTML")

    async def _handle_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        query = update.callback_query
        await query.answer()
