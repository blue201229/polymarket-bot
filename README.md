# Polymarket AI Trading Platform

A production-grade Polymarket trading platform with multiple frontends and a shared AI-assisted backend.

## Architecture

```
polymarket-ai-platform/
├── backend/          # FastAPI backend (shared by all frontends)
├── frontend/
│   ├── telegram/     # Telegram bot
│   ├── discord/      # Discord bot
│   ├── web/          # Next.js web app
│   └── mobile/       # React Native mobile app
├── infra/            # Docker, Nginx, monitoring configs
├── scripts/          # Dev and deployment scripts
└── docs/             # Architecture docs
```

## AI Capabilities

| Feature | Component | Phase |
|---|---|---|
| Market Scoring | `backend/src/ai/scoring.py` | 1 (scaffold) / 2 (live) |
| Wallet Behavior Analysis | `backend/src/ai/wallet_analysis.py` | 3 |
| Trade Signal Filtering | `backend/src/ai/trade_filter.py` | 4 |
| Parameter Optimization | `backend/src/ai/optimizer.py` | 5 |
| Anomaly Detection | `backend/src/ai/anomaly_detector.py` | 4 |
| Post-Trade Analysis | `backend/src/ai/post_trade.py` | 5 |

## AI Principles

1. **AI is an assistant layer**, not a black-box trader
2. All AI outputs are **explainable, logged, and optional**
3. **Deterministic risk rules always override AI**
4. AI scores, ranks, filters, and suggests — never executes directly
5. AI improves over time from platform data

## Phases

- **Phase 1**: Backend foundation + AI scaffolding
- **Phase 2**: Live data + execution + paper trading + basic AI scoring
- **Phase 3**: Wallet watcher + copy trading + AI wallet analysis
- **Phase 4**: Arbitrage + crypto bots + AI trade filtering + anomaly detection
- **Phase 5**: Optimization layer + full UI AI integration

## Quick Start

```bash
# Backend
cd backend && pip install -r requirements.txt
cp .env.example .env   # fill in your keys
uvicorn src.main:app --reload

# Web frontend
cd frontend/web && npm install && npm run dev

# Telegram bot
cd frontend/telegram && pip install -r requirements.txt && python main.py

# Discord bot
cd frontend/discord && pip install -r requirements.txt && python main.py

# All services via Docker
docker compose up --build
```

## Environment Variables

See `backend/.env.example` for required configuration.

Required secrets:
- `POLYMARKET_API_KEY` — Polymarket credentials
- `ANTHROPIC_API_KEY` — Claude AI (for AI features)
- `OPENAI_API_KEY` — OpenAI fallback (optional)
- `TELEGRAM_BOT_TOKEN` — Telegram bot
- `DISCORD_BOT_TOKEN` — Discord bot
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis for caching and pub/sub
