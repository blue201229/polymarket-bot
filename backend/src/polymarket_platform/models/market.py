from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DiscoveredMarket(BaseModel):
    """Normalized market row from discovery (Gamma). AI scoring attaches separately."""

    id: str
    slug: str | None = None
    question: str
    condition_id: str | None = None
    active: bool = True
    closed: bool = False
    end_date: datetime | None = None
    volume: float | None = None
    liquidity: float | None = None
    raw: dict[str, Any] = Field(default_factory=dict, description="Original API fields for audit.")
