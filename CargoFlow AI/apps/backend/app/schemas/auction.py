from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.domain import AuctionMode


class AuctionCreateRequest(BaseModel):
    load_id: Optional[str] = Field(default=None, min_length=1, max_length=36)
    load_code: Optional[str] = Field(default=None, min_length=3, max_length=24)
    mode: AuctionMode = AuctionMode.reverse
    floor_price: Optional[float] = Field(default=None, ge=0)
    ceiling_price: Optional[float] = Field(default=None, ge=0)
    starts_at: datetime
    ends_at: datetime


class AuctionResponse(BaseModel):
    id: str
    load_id: str
    load_code: str
    load_title: str
    mode: AuctionMode
    floor_price: Optional[float]
    ceiling_price: Optional[float]
    starts_at: datetime
    ends_at: datetime
    is_closed: bool
    created_at: datetime


class AuctionListResponse(BaseModel):
    items: list[AuctionResponse]
    total: int