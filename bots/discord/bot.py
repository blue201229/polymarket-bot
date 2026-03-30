from __future__ import annotations

import asyncio
from typing import Any, Optional

from backend.src.config import settings
from backend.src.core.logging import get_logger

logger = get_logger("bots.discord")

try:
    import discord
    from discord.ext import commands
    HAS_DISCORD = True
except ImportError:
    HAS_DISCORD = False


class DiscordBot:
    """
    Discord bot frontend for the Polymarket AI Trading Platform.

    Commands:
    !markets - Top AI-scored markets
    !positions - Open positions
    !trades - Recent trades
    !performance - Performance summary
    !wallets - Watched wallets
    !alerts - Recent alerts
    !optimize - AI optimization suggestions
    !status - System health
    """

    def __init__(self) -> None:
        self._bot: Optional[Any] = None
        self._api_base = "http://localhost:8000/api/v1"

    async def start(self) -> None:
        if not HAS_DISCORD:
            logger.error("discord.py not installed")
            return

        token = settings.discord_bot_token
        if not token:
            logger.error("DISCORD_BOT_TOKEN not set")
            return

        intents = discord.Intents.default()
        intents.message_content = True

        self._bot = commands.Bot(command_prefix="!", intents=intents)
        self._register_commands()

        logger.info("Discord bot starting")
        await self._bot.start(token)

    async def stop(self) -> None:
        if self._bot:
            await self._bot.close()

    def _register_commands(self) -> None:
        bot = self._bot

        @bot.event
        async def on_ready():
            logger.info("Discord bot connected", user=str(bot.user))

        @bot.command(name="markets")
        async def cmd_markets(ctx: commands.Context):
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self._api_base}/markets", params={"limit": 10})
                data = resp.json()

            markets = data.get("markets", [])
            if not markets:
                await ctx.send("No markets found.")
                return

            embed = discord.Embed(
                title="Top Markets by AI Score",
                color=discord.Color.blue(),
            )
            for m in markets[:10]:
                score = m.get("ai_score")
                score_str = f"{score:.1f}/10" if score else "N/A"
                tags = ", ".join(m.get("ai_tags", [])[:3])
                embed.add_field(
                    name=f"{m['question'][:50]}",
                    value=f"AI: {score_str} | Vol: ${m.get('volume_24h', 0):,.0f}\n{tags}",
                    inline=False,
                )
            await ctx.send(embed=embed)

        @bot.command(name="positions")
        async def cmd_positions(ctx: commands.Context):
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self._api_base}/positions")
                data = resp.json()

            positions = data.get("positions", [])
            if not positions:
                await ctx.send("No open positions.")
                return

            embed = discord.Embed(
                title=f"Open Positions ({data.get('open_count', 0)})",
                description=f"Unrealized PnL: ${data.get('total_unrealized_pnl', 0):,.2f}",
                color=discord.Color.green()
                if data.get("total_unrealized_pnl", 0) >= 0
                else discord.Color.red(),
            )
            for p in positions[:10]:
                pnl = p.get("unrealized_pnl", 0)
                embed.add_field(
                    name=f"{p['outcome'][:30]} ({p['strategy']})",
                    value=f"Entry: {p['avg_entry_price']:.3f} → {p['current_price']:.3f}\nPnL: ${pnl:+.2f}",
                    inline=True,
                )
            await ctx.send(embed=embed)

        @bot.command(name="trades")
        async def cmd_trades(ctx: commands.Context):
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self._api_base}/trades", params={"limit": 10})
                data = resp.json()

            trades = data.get("trades", [])
            if not trades:
                await ctx.send("No recent trades.")
                return

            embed = discord.Embed(title="Recent Trades", color=discord.Color.blue())
            for t in trades[:10]:
                ai_conf = t.get("ai_confidence")
                ai_str = f" | AI: {ai_conf:.1f}" if ai_conf else ""
                embed.add_field(
                    name=f"{t['side'].upper()} {t['outcome'][:25]} @ {t['price']:.3f}",
                    value=f"${t['size']:.2f} | {t['strategy']}{ai_str} | {t['status']}",
                    inline=False,
                )
            await ctx.send(embed=embed)

        @bot.command(name="performance")
        async def cmd_performance(ctx: commands.Context):
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._api_base}/performance/summary", params={"days": 7}
                )
                data = resp.json()

            pnl = data.get("net_pnl", 0)
            color = discord.Color.green() if pnl >= 0 else discord.Color.red()

            embed = discord.Embed(title="Performance (7 days)", color=color)
            embed.add_field(name="Trades", value=str(data.get("total_trades", 0)))
            embed.add_field(name="Win Rate", value=f"{data.get('win_rate', 0):.1f}%")
            embed.add_field(name="Net PnL", value=f"${pnl:,.2f}")
            embed.add_field(name="Best Trade", value=f"${data.get('best_trade', 0):,.2f}")
            embed.add_field(name="Worst Trade", value=f"${data.get('worst_trade', 0):,.2f}")
            embed.add_field(name="Max Drawdown", value=f"${data.get('max_drawdown', 0):,.2f}")
            await ctx.send(embed=embed)

        @bot.command(name="wallets")
        async def cmd_wallets(ctx: commands.Context):
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self._api_base}/wallets")
                data = resp.json()

            wallets = data.get("wallets", [])
            if not wallets:
                await ctx.send("No watched wallets.")
                return

            embed = discord.Embed(title="Watched Wallets", color=discord.Color.purple())
            for w in wallets:
                quality = w.get("ai_quality_score")
                quality_str = f"{quality:.1f}/10" if quality else "unscored"
                copy_str = " | COPY" if w.get("copy_enabled") else ""
                embed.add_field(
                    name=w.get("label", w["address"][:10]),
                    value=f"Quality: {quality_str} | {w.get('ai_strategy_class', '?')}{copy_str}",
                    inline=False,
                )
            await ctx.send(embed=embed)

        @bot.command(name="alerts")
        async def cmd_alerts(ctx: commands.Context):
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._api_base}/alerts",
                    params={"limit": 10, "unacknowledged_only": True},
                )
                data = resp.json()

            alerts = data.get("alerts", [])
            if not alerts:
                await ctx.send("No unacknowledged alerts.")
                return

            embed = discord.Embed(title="Alerts", color=discord.Color.orange())
            for a in alerts:
                embed.add_field(
                    name=f"[{a['severity'].upper()}] {a['title']}",
                    value=a["message"][:100],
                    inline=False,
                )
            await ctx.send(embed=embed)

        @bot.command(name="optimize")
        async def cmd_optimize(ctx: commands.Context):
            await ctx.send("Running AI optimization...")
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self._api_base}/ai/optimize", params={"days": 7}
                )
                data = resp.json()

            suggestions = data.get("suggestions", [])
            if not suggestions:
                await ctx.send("No parameter changes suggested.")
                return

            embed = discord.Embed(
                title="AI Optimization Suggestions",
                description=f"Confidence: {data.get('confidence', 0):.0%}",
                color=discord.Color.gold(),
            )
            for s in suggestions:
                embed.add_field(
                    name=f"{s['parameter']}: {s['current_value']} → {s['suggested_value']}",
                    value=s["reasoning"][:100],
                    inline=False,
                )
            embed.set_footer(text=data.get("overall_assessment", "")[:200])
            await ctx.send(embed=embed)

        @bot.command(name="status")
        async def cmd_status(ctx: commands.Context):
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self._api_base}/system/health")
                data = resp.json()

            embed = discord.Embed(title="System Status", color=discord.Color.green())
            embed.add_field(name="Status", value=data.get("status", "unknown"))
            embed.add_field(name="Environment", value=data.get("environment", "?"))
            embed.add_field(
                name="Paper Trading", value="Yes" if data.get("paper_trading") else "No"
            )
            embed.add_field(name="AI Enabled", value="Yes" if data.get("ai_enabled") else "No")
            await ctx.send(embed=embed)

    async def send_alert(self, channel_id: int, message: str) -> None:
        if self._bot:
            channel = self._bot.get_channel(channel_id)
            if channel:
                await channel.send(message)
