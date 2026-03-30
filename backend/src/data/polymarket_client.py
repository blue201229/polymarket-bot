"""
Polymarket API client — wraps the CLOB and Gamma APIs.

Handles:
- Market discovery (Gamma API)
- Orderbook streaming (CLOB WebSocket)
- Trade execution (CLOB REST)
- Authentication (L1/L2 signatures)
"""
import asyncio
from typing import Any, AsyncGenerator, Dict, List, Optional
from urllib.parse import urljoin

import httpx

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

GAMMA_MARKETS_ENDPOINT = "/markets"
CLOB_MARKETS_ENDPOINT = "/markets"
CLOB_ORDERBOOK_ENDPOINT = "/book"
CLOB_TRADES_ENDPOINT = "/trades"
CLOB_ORDER_ENDPOINT = "/order"


class PolymarketClient:
    """Async HTTP client for Polymarket APIs."""

    def __init__(self):
        self._gamma = httpx.AsyncClient(
            base_url=settings.polymarket_gamma_host,
            timeout=30.0,
            headers={"Accept": "application/json"},
        )
        self._clob = httpx.AsyncClient(
            base_url=settings.polymarket_host,
            timeout=30.0,
            headers={"Accept": "application/json"},
        )

    async def close(self):
        await self._gamma.aclose()
        await self._clob.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    # ── Market Discovery ──────────────────────────────────────────────────────

    async def get_markets(
        self,
        limit: int = 100,
        offset: int = 0,
        active: bool = True,
        closed: bool = False,
        category: Optional[str] = None,
        min_volume: float = 0,
    ) -> List[Dict[str, Any]]:
        """Fetch markets from Gamma API with filtering."""
        params: Dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            "active": str(active).lower(),
            "closed": str(closed).lower(),
        }
        if category:
            params["category"] = category

        try:
            resp = await self._gamma.get(GAMMA_MARKETS_ENDPOINT, params=params)
            resp.raise_for_status()
            data = resp.json()

            markets = data if isinstance(data, list) else data.get("markets", [])

            if min_volume > 0:
                markets = [m for m in markets if float(m.get("volume24hr", 0)) >= min_volume]

            return markets
        except httpx.HTTPStatusError as e:
            logger.error("polymarket_api_error", endpoint="markets", status=e.response.status_code)
            return []
        except Exception as e:
            logger.error("polymarket_client_error", endpoint="markets", error=str(e))
            return []

    async def get_market(self, condition_id: str) -> Optional[Dict[str, Any]]:
        """Get a single market by condition ID."""
        try:
            resp = await self._gamma.get(f"{GAMMA_MARKETS_ENDPOINT}/{condition_id}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("polymarket_get_market_error", condition_id=condition_id, error=str(e))
            return None

    # ── Orderbook ─────────────────────────────────────────────────────────────

    async def get_orderbook(self, token_id: str) -> Optional[Dict[str, Any]]:
        """Get current orderbook for a token."""
        try:
            resp = await self._clob.get(CLOB_ORDERBOOK_ENDPOINT, params={"token_id": token_id})
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("polymarket_orderbook_error", token_id=token_id, error=str(e))
            return None

    async def get_spread(self, token_id: str) -> Optional[float]:
        """Compute current spread for a token."""
        book = await self.get_orderbook(token_id)
        if not book:
            return None

        bids = book.get("bids", [])
        asks = book.get("asks", [])

        if not bids or not asks:
            return None

        best_bid = float(bids[0].get("price", 0))
        best_ask = float(asks[0].get("price", 0))

        if best_ask == 0:
            return None

        return (best_ask - best_bid) / best_ask

    # ── Trade History ─────────────────────────────────────────────────────────

    async def get_trades(
        self,
        maker: Optional[str] = None,
        taker: Optional[str] = None,
        market: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Fetch trade history."""
        params: Dict[str, Any] = {"limit": limit}
        if maker:
            params["maker"] = maker
        if taker:
            params["taker"] = taker
        if market:
            params["market"] = market

        try:
            resp = await self._clob.get(CLOB_TRADES_ENDPOINT, params=params)
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else data.get("data", [])
        except Exception as e:
            logger.error("polymarket_trades_error", error=str(e))
            return []

    # ── Execution ─────────────────────────────────────────────────────────────

    async def place_order(
        self,
        token_id: str,
        price: float,
        size: float,
        side: str,
        order_type: str = "GTC",
    ) -> Optional[Dict[str, Any]]:
        """
        Place a limit order on the CLOB.

        NOTE: This method requires wallet authentication.
        In paper trading mode, this method should NOT be called.
        The execution engine enforces paper trading mode — this client is agnostic.
        """
        if not settings.wallet_private_key:
            logger.error("place_order_no_wallet_key")
            return None

        order = {
            "token_id": token_id,
            "price": str(price),
            "size": str(size),
            "side": side.upper(),
            "type": order_type,
        }

        try:
            # In production, this would use the CLOB client SDK for signing
            # py-clob-client handles L1/L2 auth signatures
            resp = await self._clob.post(
                CLOB_ORDER_ENDPOINT,
                json=order,
                headers=self._get_auth_headers(order),
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("place_order_error", error=str(e))
            return None

    def _get_auth_headers(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Generate CLOB authentication headers. Stub — use py-clob-client in production."""
        return {
            "POLY_ADDRESS": settings.wallet_address,
            "POLY_SIGNATURE": "stub-signature",
            "POLY_TIMESTAMP": "0",
            "POLY_NONCE": "0",
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def normalize_market(raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Gamma API response to our internal market format."""
        tokens = raw.get("tokens", [])
        yes_token = next((t for t in tokens if t.get("outcome") == "Yes"), tokens[0] if tokens else {})

        best_bid = float(yes_token.get("bestBid", 0) or 0)
        best_ask = float(yes_token.get("bestAsk", 0) or 0)
        mid = (best_bid + best_ask) / 2 if best_bid and best_ask else None
        spread = (best_ask - best_bid) / best_ask if best_ask else None
        spread_pct = spread

        return {
            "condition_id": raw.get("conditionId", ""),
            "question_id": raw.get("questionID", ""),
            "slug": raw.get("slug", ""),
            "question": raw.get("question", ""),
            "description": raw.get("description", ""),
            "category": raw.get("category", ""),
            "tags": raw.get("tags", []),
            "end_date": raw.get("endDate"),
            "resolved": raw.get("resolved", False),
            "active": raw.get("active", True),
            "closed": raw.get("closed", False),
            "accepting_orders": raw.get("acceptingOrders", True),
            "best_bid": best_bid,
            "best_ask": best_ask,
            "mid_price": mid,
            "spread": best_ask - best_bid if best_bid and best_ask else None,
            "spread_pct": spread_pct,
            "volume_24h": float(raw.get("volume24hr", 0) or 0),
            "volume_total": float(raw.get("volume", 0) or 0),
            "liquidity": float(raw.get("liquidity", 0) or 0),
            "open_interest": float(raw.get("openInterest", 0) or 0),
            "resolution_source": raw.get("resolutionSource", ""),
            "yes_token_id": yes_token.get("tokenID", ""),
        }


_client_instance: Optional[PolymarketClient] = None


def get_polymarket_client() -> PolymarketClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = PolymarketClient()
    return _client_instance
