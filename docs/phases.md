# Delivery Phases

## Phase 1: Foundation (current)

- Monorepo with shared backend + multi-client frontends
- Deterministic market discovery and hard filtering
- AI module scaffolding:
  - async model abstraction
  - timeout controls
  - batching helpers
  - cache layer
  - structured logging
  - fallback outputs
- Basic endpoints for market listing and AI insights

## Phase 2: Live trading infrastructure

- WebSocket ingestion from market feeds
- Authenticated execution engine
- Expanded deterministic risk controls
- Paper trading mode
- Initial AI market scoring in ranking pipelines

## Phase 3: Wallet intelligence

- Wallet watcher job pipeline
- Copy-trading support
- AI wallet quality scoring + classification

## Phase 4: Advanced jobs and resilience

- Arbitrage jobs and short-duration crypto strategies
- AI trade-signal filtering
- AI anomaly detector connected to risk tightening alerts

## Phase 5: Adaptive optimization + UX hardening

- Parameter optimization suggestions with approval flow
- AI/non-AI comparison controls in frontends
- Observability and performance optimization
