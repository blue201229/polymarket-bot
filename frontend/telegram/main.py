"""
Polymarket AI Trading Platform — Telegram Bot Frontend

Commands:
/start       - Welcome and help
/markets     - Top AI-scored markets
/trades      - Recent trades
/status      - System status (paper trading, risk params)
/ai          - AI status and recent decisions
/wallet add <address> - Add wallet to watch
/wallets     - List tracked wallets
/pause       - Pause trading (authorized users only)
/resume      - Resume trading
/alerts      - Toggle real-time alerts
"""
import asyncio
import json
import logging
import os
from typing import Optional

import httpx
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

# Config
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api/v1")
ALLOWED_USERS = [
    int(u) for u in os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",") if u.strip()
]

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Authorized users set (empty = allow all)
_alert_subscribers: set = set()


def is_authorized(user_id: int) -> bool:
    if not ALLOWED_USERS:
        return True
    return user_id in ALLOWED_USERS


async def api_get(path: str) -> Optional[dict]:
    """Make API call to backend."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{BACKEND_URL}{path}")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"API error {path}: {e}")
        return None


async def api_post(path: str, data: dict) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{BACKEND_URL}{path}", json=data)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"API error POST {path}: {e}")
        return None


# ── Command Handlers ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("📊 Markets", callback_data="markets"),
            InlineKeyboardButton("📈 Trades", callback_data="trades"),
        ],
        [
            InlineKeyboardButton("🤖 AI Status", callback_data="ai_status"),
            InlineKeyboardButton("⚙️ System", callback_data="status"),
        ],
        [
            InlineKeyboardButton("👛 Wallets", callback_data="wallets"),
            InlineKeyboardButton("🔔 Alerts", callback_data="toggle_alerts"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🤖 *Polymarket AI Trading Platform*\n\n"
        "AI-assisted prediction market trading.\n\n"
        "📋 *Available Commands:*\n"
        "/markets — Top AI-scored markets\n"
        "/trades — Recent trades\n"
        "/status — System status\n"
        "/ai — AI decisions log\n"
        "/wallets — Tracked wallets\n"
        "/alerts — Toggle real-time alerts\n"
        "/pause — Pause trading _(admin)_\n"
        "/resume — Resume trading _(admin)_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup,
    )


async def cmd_markets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = await api_get("/markets?limit=10&min_score=5")
    if not data:
        await update.message.reply_text("❌ Failed to fetch markets.")
        return

    markets = data.get("markets", [])
    if not markets:
        await update.message.reply_text("No markets found.")
        return

    lines = ["📊 *Top AI-Scored Markets*\n"]
    for m in markets[:8]:
        score = m.get("ai_score")
        score_str = f"{score:.1f}/10" if score is not None else "Not scored"
        price = m.get("mid_price")
        price_str = f"{price:.2%}" if price else "N/A"
        question = m.get("question", "")[:60]
        emoji = "🟢" if score and score >= 7 else "🟡" if score and score >= 5 else "🔴"

        lines.append(
            f"{emoji} *{question}*\n"
            f"   AI Score: `{score_str}` | Price: `{price_str}`\n"
            f"   Liquidity: `${m.get('liquidity', 0):,.0f}`\n"
        )

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_trades(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = await api_get("/trades?limit=10")
    if not data:
        await update.message.reply_text("❌ Failed to fetch trades.")
        return

    stats = await api_get("/trades/stats/summary")
    trades = data.get("trades", [])

    lines = ["📈 *Recent Trades*\n"]

    if stats:
        paper = "📝 Paper" if stats.get("paper_trading") else "💰 Live"
        lines.append(
            f"{paper} | Win Rate: `{stats.get('win_rate') or 'N/A'}` | "
            f"PnL: `${stats.get('total_pnl_usdc', 0):.2f}`\n"
        )

    for t in trades[:8]:
        status_emoji = {
            "filled": "✅",
            "risk_rejected": "🚫",
            "ai_skipped": "⏭️",
            "failed": "❌",
            "pending": "⏳",
        }.get(t.get("status", ""), "❓")

        ai_conf = t.get("ai_confidence")
        ai_str = f" AI: `{ai_conf:.0%}`" if ai_conf is not None else ""
        paper_str = " 📝" if t.get("is_paper") else " 💰"

        lines.append(
            f"{status_emoji}{paper_str} {t.get('source', 'N/A')} | "
            f"`{t.get('side', '?')} {t.get('outcome', '?')}` @ "
            f"`{t.get('target_price', 0):.3f}`{ai_str}\n"
            f"   Size: `${t.get('size_usdc', 0):.2f}` | "
            f"Status: `{t.get('status', 'N/A')}`\n"
        )

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    health = await api_get("/system/health")
    risk = await api_get("/system/risk")

    if not health:
        await update.message.reply_text("❌ Backend unavailable.")
        return

    paper = "📝 Paper Trading" if health.get("paper_trading") else "💰 Live Trading"
    ai_status = "🟢 Active" if health.get("ai_available") else "🔴 Unavailable"
    paused = risk.get("trading_paused", False) if risk else False
    trading_status = "⏸️ PAUSED" if paused else "▶️ Active"

    msg = (
        f"⚙️ *System Status*\n\n"
        f"Trading Mode: {paper}\n"
        f"Trading: {trading_status}\n"
        f"AI Engine: {ai_status}\n\n"
        f"*Risk Parameters:*\n"
    )

    if risk:
        msg += (
            f"Max Position: `${risk.get('max_position_size_usdc', 0):.0f}`\n"
            f"Max Exposure: `${risk.get('max_total_exposure_usdc', 0):.0f}`\n"
            f"Max Positions: `{risk.get('max_positions', 0)}`\n"
            f"Max Spread: `{risk.get('max_spread_pct', 0):.1%}`\n"
            f"Max Slippage: `{risk.get('max_slippage_pct', 0):.1%}`\n"
        )

    if paused and risk:
        msg += f"\n⚠️ *Pause Reason:* {risk.get('pause_reason', 'Unknown')}"

    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_ai(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ai_status = await api_get("/ai/status")
    logs = await api_get("/ai/logs?limit=5")

    if not ai_status:
        await update.message.reply_text("❌ AI module unavailable.")
        return

    enabled = "🟢 Enabled" if ai_status.get("enabled") else "🔴 Disabled"
    available = "✅ Available" if ai_status.get("available") else "❌ Not configured"

    msg = (
        f"🤖 *AI Module Status*\n\n"
        f"Status: {enabled} ({available})\n"
        f"Model: `{ai_status.get('model', 'N/A')}`\n"
        f"Provider: `{ai_status.get('provider', 'none')}`\n"
        f"Timeout: `{ai_status.get('timeout_seconds', 3)}s`\n"
        f"Cache TTL: `{ai_status.get('cache_ttl_seconds', 300)}s`\n\n"
    )

    if logs:
        msg += "*Recent AI Decisions:*\n"
        for log in logs[:5]:
            component = log.get("component", "?")
            latency = log.get("latency_ms", 0)
            cached = " (cached)" if log.get("cache_hit") else ""
            success = "✅" if log.get("success") else "❌"

            output = log.get("output_parsed")
            if output and isinstance(output, dict):
                score = output.get("score") or output.get("confidence")
                decision = output.get("decision") or output.get("recommended_action")
                output_str = f"score={score}" if score else f"decision={decision}" if decision else "OK"
            else:
                output_str = "OK"

            msg += f"{success} `{component}` | {latency:.0f}ms{cached} | {output_str}\n"

    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = await api_get("/wallets?tracked_only=true")
    if data is None:
        await update.message.reply_text("❌ Failed to fetch wallets.")
        return

    if not data:
        await update.message.reply_text("No tracked wallets. Use `/wallet add <address>` to add one.")
        return

    lines = ["👛 *Tracked Wallets*\n"]
    for w in data[:10]:
        score = w.get("ai_quality_score")
        score_str = f"{score:.1f}/10" if score is not None else "Not analyzed"
        strategy = w.get("ai_strategy_class", "unknown")
        copy = "📋 Copy" if w.get("copy_trade_enabled") else ""
        emoji = "🟢" if score and score >= 7 else "🟡" if score and score >= 5 else "⚪"

        addr = w.get("address", "")
        short_addr = f"{addr[:6]}...{addr[-4:]}" if len(addr) > 10 else addr

        lines.append(
            f"{emoji} `{short_addr}` {copy}\n"
            f"   Score: `{score_str}` | Type: `{strategy}`\n"
            f"   Trades: `{w.get('total_trades', 0)}` | "
            f"Win Rate: `{w.get('win_rate') or 'N/A'}`\n"
        )

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized.")
        return

    result = await api_post("/system/trading/pause", {"reason": "telegram_operator"})
    if result:
        await update.message.reply_text("⏸️ Trading *paused*.", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ Failed to pause trading.")


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized.")
        return

    result = await api_post("/system/trading/resume", {})
    if result:
        await update.message.reply_text("▶️ Trading *resumed*.", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ Failed to resume trading.")


async def cmd_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id in _alert_subscribers:
        _alert_subscribers.discard(user_id)
        await update.message.reply_text("🔕 Real-time alerts *disabled*.", parse_mode=ParseMode.MARKDOWN)
    else:
        _alert_subscribers.add(user_id)
        await update.message.reply_text("🔔 Real-time alerts *enabled*.", parse_mode=ParseMode.MARKDOWN)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    handlers = {
        "markets": cmd_markets,
        "trades": cmd_trades,
        "status": cmd_status,
        "ai_status": cmd_ai,
        "wallets": cmd_wallets,
    }

    handler = handlers.get(query.data)
    if handler:
        # Create a fake update with the message from callback
        class FakeUpdate:
            message = query.message
            effective_user = query.from_user

        await handler(FakeUpdate(), context)
    elif query.data == "toggle_alerts":
        await cmd_alerts(update, context)


# ── WebSocket listener for real-time alerts ───────────────────────────────────

async def listen_backend_ws(app: Application) -> None:
    """Listen to backend WebSocket and forward alerts to Telegram subscribers."""
    import websockets
    ws_url = os.getenv("BACKEND_WS_URL", "ws://localhost:8000/ws")

    while True:
        try:
            async with websockets.connect(ws_url) as ws:
                logger.info(f"Connected to backend WebSocket: {ws_url}")
                async for message in ws:
                    data = json.loads(message)
                    await _handle_backend_event(app, data)
        except Exception as e:
            logger.warning(f"Backend WS disconnected: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)


async def _handle_backend_event(app: Application, data: dict) -> None:
    """Format and forward backend events to alert subscribers."""
    if not _alert_subscribers:
        return

    msg = None

    if data.get("type") == "price_change":
        return  # Too noisy — skip price updates

    elif data.get("status") == "filled":
        ai_conf = data.get("ai_confidence")
        ai_str = f"AI: {ai_conf:.0%}" if ai_conf is not None else "No AI"
        paper = "📝" if data.get("is_paper") else "💰"
        msg = (
            f"{paper} *Trade Executed*\n"
            f"{data.get('side', '?').upper()} {data.get('outcome', '?')} "
            f"@ `{data.get('executed_price', 0):.3f}`\n"
            f"Size: `${data.get('size_usdc', 0):.2f}` | {ai_str}"
        )

    elif data.get("type") in ("spread_spike", "liquidity_drop", "rapid_price_move"):
        severity = data.get("severity", "warning")
        emoji = "🚨" if severity == "critical" else "⚠️"
        msg = (
            f"{emoji} *Anomaly Detected*\n"
            f"Type: `{data.get('type', '?')}`\n"
            f"Severity: `{severity}`\n"
            f"{data.get('message', '')}"
        )

    elif data.get("type") == "copy_trade":
        msg = (
            f"📋 *Copy Trade Signal*\n"
            f"Wallet Score: `{data.get('wallet_score', 0):.1f}/10`\n"
            f"Signal: {data.get('side', '?')} @ `${data.get('size_usdc', 0):.2f}`"
        )

    if msg:
        for user_id in _alert_subscribers.copy():
            try:
                await app.bot.send_message(
                    chat_id=user_id,
                    text=msg,
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception as e:
                logger.warning(f"Failed to send alert to {user_id}: {e}")


def main() -> None:
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("markets", cmd_markets))
    application.add_handler(CommandHandler("trades", cmd_trades))
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("ai", cmd_ai))
    application.add_handler(CommandHandler("wallets", cmd_wallets))
    application.add_handler(CommandHandler("pause", cmd_pause))
    application.add_handler(CommandHandler("resume", cmd_resume))
    application.add_handler(CommandHandler("alerts", cmd_alerts))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Start backend WS listener alongside bot
    async def post_init(app):
        asyncio.create_task(listen_backend_ws(app))

    application.post_init = post_init

    logger.info("Telegram bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
