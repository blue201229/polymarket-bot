# Architecture notes

## Shared backend
- FastAPI API surface for all clients.
- Service modules partition deterministic controls from optional AI advisory logic.
- AI engine owns provider abstraction, timeout, batch execution, cache, and structured logs.

## Client roles
- Telegram/Discord are operational alert surfaces.
- Web and Mobile are visual decision-support surfaces.
- All clients consume the same backend DTOs and should never embed strategy/risk logic locally.

## AI guardrails
- AI cannot create an executable order on its own.
- Deterministic rules can ignore or downgrade AI outputs at any time.
- Every AI decision should be stored with inputs, outputs, latency, and impact classification.
