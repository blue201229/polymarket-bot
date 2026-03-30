"""
Polymarket AI Trading Platform — Discord Bot Frontend

Slash Commands:
/markets     - Top AI-scored markets with score display
/trades      - Recent trade log
/status      - System status and risk params
/ai          - AI module status and decisions
/wallets     - Tracked wallet list
/score <condition_id> - Request AI score for a market
/pause       - Pause trading (admin)
/resume      - Resume trading (admin)

Also posts real-time alerts to configured channel.
"""
import asyncio
import json
import logging
import os
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks
import httpx
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api/v1")
BACKEND_WS_URL = os.getenv("BACKEND_WS_URL", "ws://localhost:8000/ws")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")
ALERT_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0") or 0)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True


class PolymarketBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self._alert_channel: Optional[discord.TextChannel] = None

    async def setup_hook(self):
        guild = discord.Object(id=int(GUILD_ID)) if GUILD_ID else None
        if guild:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

        self.backend_ws_listener.start()
        logger.info("Discord bot setup complete")

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        if ALERT_CHANNEL_ID:
            self._alert_channel = self.get_channel(ALERT_CHANNEL_ID)

    @tasks.loop(seconds=5, reconnect=True)
    async def backend_ws_listener(self):
        """Listen to backend WebSocket and forward events to alert channel."""
        import websockets
        try:
            async with websockets.connect(BACKEND_WS_URL) as ws:
                async for message in ws:
                    data = json.loads(message)
                    await self._handle_event(data)
        except Exception as e:
            logger.warning(f"Backend WS error: {e}")

    async def _handle_event(self, data: dict):
        if not self._alert_channel:
            return

        embed = None

        if data.get("status") == "filled":
            ai_conf = data.get("ai_confidence")
            embed = discord.Embed(
                title="✅ Trade Executed",
                color=0x00FF00 if not data.get("is_paper") else 0x0099FF,
            )
            embed.add_field(name="Type", value=f"{'📝 Paper' if data.get('is_paper') else '💰 Live'}", inline=True)
            embed.add_field(name="Side", value=f"{data.get('side', '?').upper()} {data.get('outcome', '?')}", inline=True)
            embed.add_field(name="Price", value=f"{data.get('executed_price', 0):.4f}", inline=True)
            embed.add_field(name="Size", value=f"${data.get('size_usdc', 0):.2f}", inline=True)
            if ai_conf is not None:
                embed.add_field(name="AI Confidence", value=f"{ai_conf:.0%}", inline=True)
                embed.set_footer(text=f"AI Decision: {data.get('ai_decision', 'N/A')}")

        elif data.get("type") in ("spread_spike", "liquidity_drop", "rapid_price_move"):
            severity = data.get("severity", "warning")
            color = 0xFF0000 if severity == "critical" else 0xFF9900
            embed = discord.Embed(
                title=f"{'🚨' if severity == 'critical' else '⚠️'} Market Anomaly",
                description=data.get("message", ""),
                color=color,
            )
            embed.add_field(name="Type", value=data.get("type", "?"), inline=True)
            embed.add_field(name="Severity", value=severity.upper(), inline=True)
            embed.add_field(name="Action", value=data.get("suggested_action", "monitor"), inline=True)

        elif data.get("type") == "copy_trade":
            embed = discord.Embed(title="📋 Copy Trade Signal", color=0x9B59B6)
            embed.add_field(name="Wallet Score", value=f"{data.get('wallet_score', 0):.1f}/10", inline=True)
            embed.add_field(name="Signal", value=f"{data.get('side', '?').upper()}", inline=True)
            embed.add_field(name="Size", value=f"${data.get('size_usdc', 0):.2f}", inline=True)

        if embed:
            try:
                await self._alert_channel.send(embed=embed)
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")


bot = PolymarketBot()


async def api_get(path: str) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{BACKEND_URL}{path}")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"API error {path}: {e}")
        return None


async def api_post(path: str, data: dict = None) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{BACKEND_URL}{path}", json=data or {})
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"API error POST {path}: {e}")
        return None


# ── Slash Commands ────────────────────────────────────────────────────────────

@bot.tree.command(name="markets", description="Show top AI-scored Polymarket markets")
@app_commands.describe(min_score="Minimum AI score (0-10)", limit="Number of markets to show")
async def slash_markets(interaction: discord.Interaction, min_score: float = 5.0, limit: int = 8):
    await interaction.response.defer()

    data = await api_get(f"/markets?limit={limit}&min_score={min_score}")
    if not data:
        await interaction.followup.send("❌ Failed to fetch markets.")
        return

    markets = data.get("markets", [])
    if not markets:
        await interaction.followup.send("No markets found with the specified criteria.")
        return

    embed = discord.Embed(
        title=f"📊 Top AI-Scored Markets (min score: {min_score})",
        color=0x1DA1F2,
    )

    for m in markets[:limit]:
        score = m.get("ai_score")
        score_str = f"{score:.1f}/10" if score is not None else "Not scored"
        price = m.get("mid_price")
        price_str = f"{price:.2%}" if price else "N/A"
        reasoning = m.get("ai_reasoning", "")
        reasoning_preview = reasoning[:80] + "..." if len(reasoning) > 80 else reasoning

        emoji = "🟢" if score and score >= 7 else "🟡" if score and score >= 5 else "🔴"

        embed.add_field(
            name=f"{emoji} {m.get('question', '')[:50]}",
            value=f"Score: **{score_str}** | Price: `{price_str}` | Liquidity: `${m.get('liquidity', 0):,.0f}`\n_{reasoning_preview}_",
            inline=False,
        )

    embed.set_footer(text=f"Showing {len(markets)} markets | AI scores are advisory only")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="trades", description="Show recent trades")
async def slash_trades(interaction: discord.Interaction, limit: int = 8):
    await interaction.response.defer()

    data = await api_get(f"/trades?limit={limit}")
    stats = await api_get("/trades/stats/summary")

    if not data:
        await interaction.followup.send("❌ Failed to fetch trades.")
        return

    trades = data.get("trades", [])
    paper = stats.get("paper_trading", True) if stats else True
    mode_str = "📝 Paper Trading" if paper else "💰 Live Trading"

    embed = discord.Embed(
        title=f"📈 Recent Trades | {mode_str}",
        color=0x00FF7F,
    )

    if stats:
        embed.add_field(name="Total Trades", value=str(stats.get("filled", 0)), inline=True)
        embed.add_field(name="Win Rate", value=str(stats.get("win_rate") or "N/A"), inline=True)
        embed.add_field(name="Total PnL", value=f"${stats.get('total_pnl_usdc', 0):.2f}", inline=True)

    for t in trades[:limit]:
        status_emoji = {
            "filled": "✅",
            "risk_rejected": "🚫",
            "ai_skipped": "⏭️",
            "failed": "❌",
        }.get(t.get("status", ""), "❓")

        ai_conf = t.get("ai_confidence")
        ai_str = f" | AI: {ai_conf:.0%}" if ai_conf is not None else ""
        source = t.get("source", "?")

        embed.add_field(
            name=f"{status_emoji} {source.upper()} | {t.get('side', '?')} {t.get('outcome', '?')}",
            value=f"Price: `{t.get('target_price', 0):.3f}` | Size: `${t.get('size_usdc', 0):.2f}`{ai_str}",
            inline=False,
        )

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="status", description="System status and risk parameters")
async def slash_status(interaction: discord.Interaction):
    await interaction.response.defer()

    health = await api_get("/system/health")
    risk = await api_get("/system/risk")

    if not health:
        await interaction.followup.send("❌ Backend unavailable.")
        return

    paper = health.get("paper_trading", True)
    paused = risk.get("trading_paused", False) if risk else False
    ai_ok = health.get("ai_available", False)

    color = 0xFF0000 if paused else (0x00FF00 if not paper else 0x0099FF)

    embed = discord.Embed(
        title="⚙️ System Status",
        color=color,
    )
    embed.add_field(name="Mode", value="📝 Paper Trading" if paper else "💰 Live Trading", inline=True)
    embed.add_field(name="Trading", value="⏸️ PAUSED" if paused else "▶️ Active", inline=True)
    embed.add_field(name="AI Engine", value="🟢 Active" if ai_ok else "🔴 Unavailable", inline=True)

    if risk:
        embed.add_field(name="Max Position", value=f"${risk.get('max_position_size_usdc', 0):.0f}", inline=True)
        embed.add_field(name="Max Exposure", value=f"${risk.get('max_total_exposure_usdc', 0):.0f}", inline=True)
        embed.add_field(name="Max Spread", value=f"{risk.get('max_spread_pct', 0):.1%}", inline=True)

    if paused and risk:
        embed.add_field(name="Pause Reason", value=risk.get("pause_reason", "Unknown"), inline=False)

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="ai", description="AI module status and recent decisions")
async def slash_ai(interaction: discord.Interaction):
    await interaction.response.defer()

    ai_status = await api_get("/ai/status")
    logs = await api_get("/ai/logs?limit=5")

    if not ai_status:
        await interaction.followup.send("❌ AI module unavailable.")
        return

    embed = discord.Embed(
        title="🤖 AI Module",
        color=0x9B59B6 if ai_status.get("available") else 0x95A5A6,
    )
    embed.add_field(name="Status", value="🟢 Available" if ai_status.get("available") else "🔴 Unavailable", inline=True)
    embed.add_field(name="Provider", value=ai_status.get("provider", "none"), inline=True)
    embed.add_field(name="Model", value=ai_status.get("model", "N/A"), inline=True)
    embed.add_field(name="Timeout", value=f"{ai_status.get('timeout_seconds', 3)}s", inline=True)
    embed.add_field(name="Cache TTL", value=f"{ai_status.get('cache_ttl_seconds', 300)}s", inline=True)

    if logs:
        log_lines = []
        for l in logs[:5]:
            status = "✅" if l.get("success") else "❌"
            cached = " (cached)" if l.get("cache_hit") else ""
            log_lines.append(f"{status} `{l.get('component', '?')}` — {l.get('latency_ms', 0):.0f}ms{cached}")
        embed.add_field(name="Recent Calls", value="\n".join(log_lines), inline=False)

    embed.set_footer(text="AI is advisory only. Risk engine has final authority.")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="pause", description="Pause trading (admin only)")
async def slash_pause(interaction: discord.Interaction, reason: str = "discord_admin"):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
        return

    result = await api_post(f"/system/trading/pause?reason={reason}")
    if result:
        await interaction.response.send_message(f"⏸️ Trading paused. Reason: `{reason}`")
    else:
        await interaction.response.send_message("❌ Failed to pause trading.")


@bot.tree.command(name="resume", description="Resume trading (admin only)")
async def slash_resume(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
        return

    result = await api_post("/system/trading/resume")
    if result:
        await interaction.response.send_message("▶️ Trading resumed.")
    else:
        await interaction.response.send_message("❌ Failed to resume trading.")


if __name__ == "__main__":
    if not BOT_TOKEN:
        logger.error("DISCORD_BOT_TOKEN not set")
    else:
        logger.info("Starting Discord bot...")
        bot.run(BOT_TOKEN)
