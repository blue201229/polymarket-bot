# Polymarket platform — backend

Python 3.11+ shared API for market discovery, execution (later phases), and the AI assistant layer.

## Run locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn polymarket_platform.main:app --reload --host 0.0.0.0 --port 8000
```

- Health: `GET http://localhost:8000/health`
- Discover markets: `GET http://localhost:8000/api/v1/markets/discover`

Environment variables are documented in `.env.example`.
