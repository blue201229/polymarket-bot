# Polymarket AI-Assisted Trading Platform (Monorepo)

This repository contains a **shared backend** and **4 frontend clients**:

1. Telegram
2. Discord
3. Website
4. Mobile app

The platform is built around a strict principle:

- Deterministic trading/risk logic is authoritative.
- AI is an assistant layer used to score, rank, filter, and suggest.
- AI can be disabled at runtime.
- AI outputs are explainable, logged, and time-bounded.

---

## Architecture plan

### Deterministic core (authoritative)

- Market discovery + hard filters
- Execution/risk guardrails
- Position sizing and safety checks
- Non-AI fallback behavior

### AI assistant layer (optional, explainable)

- Market scoring
- Wallet behavior analysis
- Trade signal filtering
- Parameter optimization suggestions
- Anomaly/risk detection
- Post-trade review hooks

AI is never allowed to place trades directly; it can only influence candidate ranking and recommendations.

---

## Monorepo structure

```text
backend/
  pyproject.toml
  src/
    main.py
    api/
      router.py
      routes/
        health.py
        markets.py
        ai.py
    core/
      config.py
      logging_utils.py
      models.py
      risk_engine.py
    services/
      market_discovery.py
    ai/
      __init__.py
      ai_engine.py
      scoring.py
      wallet_analysis.py
      trade_filter.py
      optimizer.py
      anomaly_detector.py
      prompts/
        market_prompt.txt
        wallet_prompt.txt
        trade_prompt.txt

frontends/
  telegram/
    bot.py
  discord/
    bot.py
  web/
    index.html
    app.js
    styles.css
  mobile/
    App.tsx
    package.json

docs/
  phases.md
```

---

## Phase roadmap

### Phase 1 (implemented here)

- Backend foundation
- Market discovery service (mock + hard filters)
- Base API architecture
- AI module scaffolding (async, batching, caching, timeout, fallback)
- Frontend client skeletons wired to backend

### Phase 2

- Live WebSocket ingestion
- Authenticated execution engine
- Deterministic risk engine expansion
- Paper trading mode
- Basic AI scoring integrated into prioritization and UI toggles

### Phase 3

- Wallet watcher/copy-trading pipeline
- AI wallet profiling for wallet-quality filtering

### Phase 4

- Arbitrage and short-duration bot jobs
- AI trade filtering and anomaly detection in runtime monitoring

### Phase 5

- Parameter optimization loop with approval workflow
- UI exposure for suggestions/insights
- Performance and observability hardening

---

## Quick start (Phase 1)

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
PYTHONPATH=src uvicorn main:app --reload --port 8000
```

### Web frontend

```bash
cd frontends/web
python3 -m http.server 8080
```

Then open:

- Web client: http://localhost:8080
- API docs: http://localhost:8000/docs

---

## Important safety constraints

- AI outputs are advisory only.
- Risk checks override AI every time.
- AI timeout defaults to <= 2.5s and falls back to deterministic behavior.
- Input/output/latency/decision impact are logged for AI calls.
