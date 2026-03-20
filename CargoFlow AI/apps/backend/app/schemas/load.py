from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.domain import LoadStatus, VehicleKind


class LoadCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    origin_label: str = Field(min_length=2, max_length=160)
    destination_label: str = Field(min_length=2, max_length=160)
    pickup_window_start: datetime
    delivery_window_end: datetime
    budget_amount: Optional[float] = Field(default=None, ge=0)
    vehicle_kind: VehicleKind
    adr_required: bool = False
    preferred_vehicle_id: Optional[str] = Field(default=None, max_length=36)


class LoadResponse(BaseModel):
    id: str
    company_id: str
    preferred_vehicle_id: Optional[str]
    code: str
    title: str
    origin_label: str
    destination_label: str
    pickup_window_start: datetime
    delivery_window_end: datetime
    budget_amount: Optional[float]
    vehicle_kind: VehicleKind
    adr_required: bool
    status: LoadStatus
    created_at: datetime


class LoadListResponse(BaseModel):
    items: list[LoadResponse]
    total: int