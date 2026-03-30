from __future__ import annotations

from typing import Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.src.core.logging import get_logger

logger = get_logger("utils.http")

_client: Optional[httpx.AsyncClient] = None


async def get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            follow_redirects=True,
        )
    return _client


async def close_http_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def http_get(url: str, params: Optional[dict] = None, headers: Optional[dict] = None) -> Any:
    client = await get_http_client()
    response = await client.get(url, params=params, headers=headers)
    response.raise_for_status()
    return response.json()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def http_post(
    url: str,
    json: Optional[dict] = None,
    data: Optional[dict] = None,
    headers: Optional[dict] = None,
) -> Any:
    client = await get_http_client()
    response = await client.post(url, json=json, data=data, headers=headers)
    response.raise_for_status()
    return response.json()
