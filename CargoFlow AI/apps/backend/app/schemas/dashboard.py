from pydantic import BaseModel


class MetricCardResponse(BaseModel):
    label: str
    value: str
    tone: str


class TimelineItemResponse(BaseModel):
    id: str
    title: str
    subtitle: str
    meta: str
    status: str


class CarrierDashboardResponse(BaseModel):
    metrics: list[MetricCardResponse]
    active_loads: list[TimelineItemResponse]
    live_auctions: list[TimelineItemResponse]
    compliance: list[TimelineItemResponse]


class DriverDashboardResponse(BaseModel):
    metrics: list[MetricCardResponse]
    assigned_trips: list[TimelineItemResponse]
    today_checklist: list[TimelineItemResponse]
    alerts: list[TimelineItemResponse]
