# Polymarket AI Trading Platform

Production-grade, AI-assisted prediction market trading platform with multiple frontends and a shared backend.

## Architecture

```
polymarket-ai-platform/
├── backend/                    # Python FastAPI backend
│   ├── src/
│   │   ├── ai/                 # AI module (scoring, filtering, optimization)
│   │   │   ├── ai_engine.py    # Unified AI engine (Anthropic/OpenAI)
│   │   │   ├── scoring.py      # Market scoring
│   │   │   ├── wallet_analysis.py
│   │   │   ├── trade_filter.py # Trade signal filtering
│   │   │   ├── optimizer.py    # Parameter optimization
│   │   │   ├── anomaly_detector.py
│   │   │   ├── post_trade.py   # Post-trade analysis
│   │   │   └── prompts/        # Structured AI prompt templates
│   │   ├── api/routes/         # REST API endpoints
│   │   ├── core/               # Database, events, logging
│   │   ├── models/             # SQLAlchemy models
│   │   ├── services/           # Business logic
│   │   │   ├── execution_engine.py
│   │   │   ├── risk_engine.py
│   │   │   ├── market_discovery.py
│   │   │   ├── wallet_watcher.py
│   │   │   ├── anomaly_monitor.py
│   │   │   ├── performance.py
│   │   │   ├── scheduler.py
│   │   │   └── strategies/     # Trading strategies
│   │   └── utils/
│   └── tests/                  # Test suite
├── frontend/
│   ├── web/                    # React + Vite + TypeScript
│   └── mobile/                 # React Native (Expo)
├── bots/
│   ├── telegram/               # Telegram bot
│   └── discord/                # Discord bot
├── infrastructure/             # Docker, deployment configs
└── docker-compose.yml
```

## Core Design Principles

### AI as Assistant, Not Oracle

- AI **scores, ranks, filters, and suggests** — it never directly places trades
- All AI outputs are **explainable, logged, and optional** (can be disabled)
- **Deterministic logic (risk engine, execution rules) ALWAYS overrides AI**
- AI improves over time using data collected by the system

### Execution Pipeline

```
Strategy Signal → AI Filter → Risk Engine → Execute/Paper → Record
                  (advisory)   (FINAL SAY)
```

The risk engine has absolute veto power. AI can suggest tighter constraints, but never looser ones.

## AI Capabilities

| Module | Purpose | Input | Output |
|--------|---------|-------|--------|
| Market Scorer | Prioritize markets | Market data | Score 0-10, tags, reasoning |
| Trade Filter | Evaluate signals | Signal + context | Confidence, size modifier |
| Wallet Analyzer | Profile wallets | Wallet history | Quality score, strategy class |
| Anomaly Detector | Risk monitoring | Market snapshots | Anomaly alerts, risk level |
| Parameter Optimizer | Tune parameters | Performance data | Suggestions (never auto-applied) |
| Post-Trade Analyzer | Review trades | Trade history | Insights, improvement suggestions |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/markets` | GET | List markets with AI scores |
| `/api/v1/markets/discover` | POST | Trigger market discovery |
| `/api/v1/trades` | GET | List trades |
| `/api/v1/trades/signal` | POST | Submit trade signal |
| `/api/v1/trades/stats` | GET | Trade statistics |
| `/api/v1/positions` | GET | List positions |
| `/api/v1/wallets` | GET/POST/DELETE | Manage watched wallets |
| `/api/v1/wallets/{addr}/analyze` | POST | AI wallet analysis |
| `/api/v1/ai/logs` | GET | AI call logs |
| `/api/v1/ai/impact` | GET | AI vs non-AI comparison |
| `/api/v1/ai/optimize` | POST | Run parameter optimization |
| `/api/v1/ai/analyze` | POST | Run post-trade analysis |
| `/api/v1/performance/summary` | GET | Performance metrics |
| `/api/v1/alerts` | GET | List alerts |
| `/api/v1/system/health` | GET | Health check |

## Trading Strategies

- **Value**: Edge-based entry with Kelly-inspired sizing
- **Momentum**: Price momentum with volume confirmation
- **Arbitrage**: Binary market mispricing detection
- **Copy Trade**: Replicate high-quality wallet trades (AI quality gate)

## Frontends

1. **Web Dashboard** — Full-featured React app with AI score columns, comparison toggles, optimization panel
2. **Mobile App** — Simplified AI scores, position monitoring, push alerts
3. **Telegram Bot** — Commands: `/markets`, `/positions`, `/trades`, `/performance`, `/optimize`
4. **Discord Bot** — Rich embeds: `!markets`, `!positions`, `!trades`, `!performance`, `!optimize`

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose (optional)

### Backend

```bash
cd backend
cp .env.example .env
# Edit .env with your API keys
pip install -e ".[dev]"
uvicorn backend.src.main:app --reload
```

### Web Frontend

```bash
cd frontend/web
npm install
npm run dev
```

### Docker

```bash
docker-compose up -d
```

### Run Tests

```bash
python3 -m pytest backend/tests/ -v
```

## Configuration

All configuration via environment variables (see `backend/.env.example`):

- `AI_ENABLED` — Toggle all AI features
- `PAPER_TRADING` — Paper/live mode
- `AI_DEFAULT_PROVIDER` — `anthropic` or `openai`
- `AI_TIMEOUT_SECONDS` — Max AI call duration (default: 3s)
- `MAX_POSITION_SIZE_USD` — Per-market position limit
- `MAX_DAILY_LOSS_USD` — Daily loss limit

## Risk Controls

Hard limits enforced by the risk engine (never overridden by AI):

- Maximum position size per market
- Daily loss limit
- Maximum open positions
- Single trade size cap
- Minimum liquidity requirement
- Cooldown between trades
- AI size modifier clamping (0.5x–1.2x only)

## License

MIT
