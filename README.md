# Polymarket AI Platform

AI-assisted Polymarket trading platform monorepo with one shared backend and four clients: Telegram, Discord, Web, and Mobile.

## Architecture plan

### Product shape
- **Shared backend**: market discovery, orchestration, execution, risk, paper trading, copy-trading, AI services, monitoring.
- **Clients**:
  - `clients/telegram/` for operator alerts and chat workflows
  - `clients/discord/` for community/desk workflows
  - `apps/web/` for power-user dashboards and AI explainability
  - `apps/mobile/` for compact monitoring and high-confidence opportunities
- **Shared contracts**: typed DTOs and API response shapes consumed by UI surfaces.

### Deterministic vs AI boundaries
- Deterministic services own hard filters, risk limits, execution, auth, and final trade eligibility.
- AI services are advisory only and can score, rank, filter, explain, and suggest parameter changes.
- AI outputs are cached, time-limited, logged, explainable, and optional.
- If AI fails or times out, deterministic flows continue with safe fallback behavior.

### Phase roadmap
1. **Phase 1**: backend foundation, architecture contracts, market discovery scaffold, AI module scaffold.
2. **Phase 2**: live data ingestion, execution engine, risk engine, paper trading, basic AI scoring in discovery.
3. **Phase 3**: wallet watcher, copy trading, AI wallet behavior analysis.
4. **Phase 4**: arbitrage jobs, short-duration crypto bots, AI trade filtering, anomaly detection.
5. **Phase 5**: parameter optimization, UI AI panels, monitoring/performance improvements.

## Monorepo structure

```text
backend/
  pyproject.toml
  src/
    ai/
      ai_engine.py
      scoring.py
      wallet_analysis.py
      trade_filter.py
      optimizer.py
      anomaly_detector.py
      prompts/
    app/
      main.py
      api/routes/
      core/
      domain/
      services/
apps/
  web/
  mobile/
clients/
  telegram/
  discord/
shared/
  contracts/
docs/
```

## Phase 1 implementation status

Implemented in this iteration:
- FastAPI backend foundation with health, blueprint, AI capability, and market discovery routes.
- Async AI engine with provider abstraction, batching, cache, timeout, structured logging, and fallback responses.
- Market discovery service that applies deterministic hard filters before optional AI market scoring.
- Shared TypeScript contracts for market discovery responses and AI score rendering.
- Telegram/Discord formatter scaffolds and Web/Mobile component skeletons wired to shared contracts.

Not implemented yet:
- Authenticated execution against Polymarket
- Risk engine enforcement for live orders
- Wallet watching/copy trading pipelines
- Arbitrage/crypto bots
- Parameter optimization review workflow

## Run Phase 1 backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e backend
uvicorn app.main:app --app-dir backend/src --reload
```

Then open `http://127.0.0.1:8000/docs`.
