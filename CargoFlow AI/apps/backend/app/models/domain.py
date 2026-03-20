import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class UserRole(str, enum.Enum):
    carrier_owner = "carrier_owner"
    dispatcher = "dispatcher"
    driver = "driver"
    admin = "admin"


class VehicleKind(str, enum.Enum):
    frigo = "frigo"
    telonato = "telonato"
    cassonato = "cassonato"
    cisterna = "cisterna"
    furgone = "furgone"


class DocumentType(str, enum.Enum):
    durc = "durc"
    insurance = "insurance"
    carrier_register = "carrier_register"
    driving_license = "driving_license"
    cmr = "cmr"
    ddt = "ddt"


class DocumentStatus(str, enum.Enum):
    pending = "pending"
    valid = "valid"
    expired = "expired"
    rejected = "rejected"


class LoadStatus(str, enum.Enum):
    draft = "draft"
    open = "open"
    auction_live = "auction_live"
    assigned = "assigned"
    cancelled = "cancelled"
    completed = "completed"


class AuctionMode(str, enum.Enum):
    reverse = "reverse"
    forward = "forward"


class BidStatus(str, enum.Enum):
    active = "active"
    winning = "winning"
    outbid = "outbid"
    cancelled = "cancelled"


class TripStatus(str, enum.Enum):
    draft = "draft"
    assigned = "assigned"
    heading_to_pickup = "heading_to_pickup"
    arrived_at_pickup = "arrived_at_pickup"
    loaded = "loaded"
    in_transit = "in_transit"
    arrived_at_delivery = "arrived_at_delivery"
    delivered = "delivered"
    closed = "closed"


class Company(Base, TimestampMixin):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    legal_name: Mapped[str] = mapped_column(String(160), nullable=False)
    vat_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    register_number: Mapped[Optional[str]] = mapped_column(String(64))
    insurance_policy_number: Mapped[Optional[str]] = mapped_column(String(64))
    country_code: Mapped[str] = mapped_column(String(2), default="IT")
    compliance_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    reputation_score: Mapped[float] = mapped_column(Float, default=0.0)

    users: Mapped[list["User"]] = relationship(back_populates="company")
    vehicles: Mapped[list["Vehicle"]] = relationship(back_populates="company")
    route_preferences: Mapped[list["RoutePreference"]] = relationship(back_populates="company")
    compliance_documents: Mapped[list["ComplianceDocument"]] = relationship(back_populates="company")
    loads: Mapped[list["Load"]] = relationship(back_populates="company")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id: Mapped[Optional[str]] = mapped_column(ForeignKey("companies.id"))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(String(32))
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    company: Mapped[Optional["Company"]] = relationship(back_populates="users")
    assigned_trips: Mapped[list["Trip"]] = relationship(back_populates="driver")
    bids: Mapped[list["Bid"]] = relationship(back_populates="bidder")
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="author")
    created_invites: Mapped[list["InviteToken"]] = relationship(back_populates="created_by")


class InviteToken(Base, TimestampMixin):
    __tablename__ = "invite_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    created_by_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"))
    token: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.driver)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    company: Mapped["Company"] = relationship()
    created_by: Mapped[Optional["User"]] = relationship(back_populates="created_invites")


class Vehicle(Base, TimestampMixin):
    __tablename__ = "vehicles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    plate_number: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    vehicle_kind: Mapped[VehicleKind] = mapped_column(Enum(VehicleKind), nullable=False)
    has_bi_temperature: Mapped[bool] = mapped_column(Boolean, default=False)
    has_meat_hooks: Mapped[bool] = mapped_column(Boolean, default=False)
    has_thermograph: Mapped[bool] = mapped_column(Boolean, default=False)
    has_coil_well: Mapped[bool] = mapped_column(Boolean, default=False)
    has_lift_axle: Mapped[bool] = mapped_column(Boolean, default=False)
    adr_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    max_payload_kg: Mapped[Optional[int]] = mapped_column(Integer)

    company: Mapped["Company"] = relationship(back_populates="vehicles")
    loads: Mapped[list["Load"]] = relationship(back_populates="preferred_vehicle")
    trips: Mapped[list["Trip"]] = relationship(back_populates="vehicle")


class RoutePreference(Base, TimestampMixin):
    __tablename__ = "route_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    origin_country: Mapped[str] = mapped_column(String(2), nullable=False)
    destination_country: Mapped[str] = mapped_column(String(2), nullable=False)
    origin_region: Mapped[Optional[str]] = mapped_column(String(80))
    destination_region: Mapped[Optional[str]] = mapped_column(String(80))
    priority_rank: Mapped[int] = mapped_column(Integer, default=1)

    company: Mapped["Company"] = relationship(back_populates="route_preferences")


class ComplianceDocument(Base, TimestampMixin):
    __tablename__ = "compliance_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id: Mapped[Optional[str]] = mapped_column(ForeignKey("companies.id"))
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"))
    document_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus), default=DocumentStatus.pending)
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    company: Mapped[Optional["Company"]] = relationship(back_populates="compliance_documents")


class Load(Base, TimestampMixin):
    __tablename__ = "loads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    preferred_vehicle_id: Mapped[Optional[str]] = mapped_column(ForeignKey("vehicles.id"))
    code: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    origin_label: Mapped[str] = mapped_column(String(160), nullable=False)
    destination_label: Mapped[str] = mapped_column(String(160), nullable=False)
    pickup_window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivery_window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    budget_amount: Mapped[Optional[float]] = mapped_column(Float)
    vehicle_kind: Mapped[VehicleKind] = mapped_column(Enum(VehicleKind), nullable=False)
    adr_required: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[LoadStatus] = mapped_column(Enum(LoadStatus), default=LoadStatus.draft)

    company: Mapped["Company"] = relationship(back_populates="loads")
    preferred_vehicle: Mapped[Optional["Vehicle"]] = relationship(back_populates="loads")
    auction: Mapped[Optional["Auction"]] = relationship(back_populates="load", uselist=False)
    trip: Mapped[Optional["Trip"]] = relationship(back_populates="load", uselist=False)


class Auction(Base, TimestampMixin):
    __tablename__ = "auctions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    load_id: Mapped[str] = mapped_column(ForeignKey("loads.id"), unique=True, nullable=False)
    mode: Mapped[AuctionMode] = mapped_column(Enum(AuctionMode), default=AuctionMode.reverse)
    floor_price: Mapped[Optional[float]] = mapped_column(Float)
    ceiling_price: Mapped[Optional[float]] = mapped_column(Float)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)

    load: Mapped["Load"] = relationship(back_populates="auction")
    bids: Mapped[list["Bid"]] = relationship(back_populates="auction")


class Bid(Base, TimestampMixin):
    __tablename__ = "bids"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    auction_id: Mapped[str] = mapped_column(ForeignKey("auctions.id"), nullable=False)
    bidder_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[BidStatus] = mapped_column(Enum(BidStatus), default=BidStatus.active)

    auction: Mapped["Auction"] = relationship(back_populates="bids")
    bidder: Mapped["User"] = relationship(back_populates="bids")


class Trip(Base, TimestampMixin):
    __tablename__ = "trips"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    load_id: Mapped[str] = mapped_column(ForeignKey("loads.id"), unique=True, nullable=False)
    driver_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"))
    vehicle_id: Mapped[Optional[str]] = mapped_column(ForeignKey("vehicles.id"))
    current_status: Mapped[TripStatus] = mapped_column(Enum(TripStatus), default=TripStatus.draft)
    pickup_geofence_radius_m: Mapped[int] = mapped_column(Integer, default=300)
    delivery_geofence_radius_m: Mapped[int] = mapped_column(Integer, default=300)
    latest_latitude: Mapped[Optional[float]] = mapped_column(Float)
    latest_longitude: Mapped[Optional[float]] = mapped_column(Float)

    load: Mapped["Load"] = relationship(back_populates="trip")
    driver: Mapped[Optional["User"]] = relationship(back_populates="assigned_trips")
    vehicle: Mapped[Optional["Vehicle"]] = relationship(back_populates="trips")
    status_events: Mapped[list["TripStatusEvent"]] = relationship(back_populates="trip")
    chat_messages: Mapped[list["ChatMessage"]] = relationship(back_populates="trip")


class TripStatusEvent(Base):
    __tablename__ = "trip_status_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), nullable=False)
    status: Mapped[TripStatus] = mapped_column(Enum(TripStatus), nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="system")
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    emitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    trip: Mapped["Trip"] = relationship(back_populates="status_events")


class ChatMessage(Base, TimestampMixin):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), nullable=False)
    author_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"))
    message_type: Mapped[str] = mapped_column(String(32), default="text")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_system_generated: Mapped[bool] = mapped_column(Boolean, default=False)

    trip: Mapped["Trip"] = relationship(back_populates="chat_messages")
    author: Mapped[Optional["User"]] = relationship(back_populates="messages")
