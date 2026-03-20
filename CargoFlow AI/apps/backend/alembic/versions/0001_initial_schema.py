"""initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-03-16 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


user_role_enum = sa.Enum("carrier_owner", "dispatcher", "driver", "admin", name="userrole")
vehicle_kind_enum = sa.Enum("frigo", "telonato", "cassonato", "cisterna", "furgone", name="vehiclekind")
document_type_enum = sa.Enum("durc", "insurance", "carrier_register", "driving_license", "cmr", "ddt", name="documenttype")
document_status_enum = sa.Enum("pending", "valid", "expired", "rejected", name="documentstatus")
load_status_enum = sa.Enum("draft", "open", "auction_live", "assigned", "cancelled", "completed", name="loadstatus")
auction_mode_enum = sa.Enum("reverse", "forward", name="auctionmode")
bid_status_enum = sa.Enum("active", "winning", "outbid", "cancelled", name="bidstatus")
trip_status_enum = sa.Enum(
    "draft",
    "assigned",
    "heading_to_pickup",
    "arrived_at_pickup",
    "loaded",
    "in_transit",
    "arrived_at_delivery",
    "delivered",
    "closed",
    name="tripstatus",
)


def upgrade() -> None:
    bind = op.get_bind()
    enum_types = [
        user_role_enum,
        vehicle_kind_enum,
        document_type_enum,
        document_status_enum,
        load_status_enum,
        auction_mode_enum,
        bid_status_enum,
        trip_status_enum,
    ]
    for enum_type in enum_types:
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "companies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("legal_name", sa.String(length=160), nullable=False),
        sa.Column("vat_number", sa.String(length=32), nullable=False),
        sa.Column("register_number", sa.String(length=64), nullable=True),
        sa.Column("insurance_policy_number", sa.String(length=64), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("compliance_blocked", sa.Boolean(), nullable=False),
        sa.Column("reputation_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vat_number"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("phone_number", sa.String(length=32), nullable=True),
        sa.Column("first_name", sa.String(length=80), nullable=False),
        sa.Column("last_name", sa.String(length=80), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "invite_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("token", sa.String(length=32), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invite_tokens_token"), "invite_tokens", ["token"], unique=True)

    op.create_table(
        "vehicles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("plate_number", sa.String(length=16), nullable=False),
        sa.Column("vehicle_kind", vehicle_kind_enum, nullable=False),
        sa.Column("has_bi_temperature", sa.Boolean(), nullable=False),
        sa.Column("has_meat_hooks", sa.Boolean(), nullable=False),
        sa.Column("has_thermograph", sa.Boolean(), nullable=False),
        sa.Column("has_coil_well", sa.Boolean(), nullable=False),
        sa.Column("has_lift_axle", sa.Boolean(), nullable=False),
        sa.Column("adr_enabled", sa.Boolean(), nullable=False),
        sa.Column("max_payload_kg", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plate_number"),
    )

    op.create_table(
        "route_preferences",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("origin_country", sa.String(length=2), nullable=False),
        sa.Column("destination_country", sa.String(length=2), nullable=False),
        sa.Column("origin_region", sa.String(length=80), nullable=True),
        sa.Column("destination_region", sa.String(length=80), nullable=True),
        sa.Column("priority_rank", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "compliance_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("document_type", document_type_enum, nullable=False),
        sa.Column("status", document_status_enum, nullable=False),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "loads",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("preferred_vehicle_id", sa.String(length=36), nullable=True),
        sa.Column("code", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("origin_label", sa.String(length=160), nullable=False),
        sa.Column("destination_label", sa.String(length=160), nullable=False),
        sa.Column("pickup_window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivery_window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("budget_amount", sa.Float(), nullable=True),
        sa.Column("vehicle_kind", vehicle_kind_enum, nullable=False),
        sa.Column("adr_required", sa.Boolean(), nullable=False),
        sa.Column("status", load_status_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["preferred_vehicle_id"], ["vehicles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "auctions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("load_id", sa.String(length=36), nullable=False),
        sa.Column("mode", auction_mode_enum, nullable=False),
        sa.Column("floor_price", sa.Float(), nullable=True),
        sa.Column("ceiling_price", sa.Float(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_closed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["load_id"], ["loads.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("load_id"),
    )

    op.create_table(
        "bids",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("auction_id", sa.String(length=36), nullable=False),
        sa.Column("bidder_id", sa.String(length=36), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("status", bid_status_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["auction_id"], ["auctions.id"]),
        sa.ForeignKeyConstraint(["bidder_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "trips",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("load_id", sa.String(length=36), nullable=False),
        sa.Column("driver_id", sa.String(length=36), nullable=True),
        sa.Column("vehicle_id", sa.String(length=36), nullable=True),
        sa.Column("current_status", trip_status_enum, nullable=False),
        sa.Column("pickup_geofence_radius_m", sa.Integer(), nullable=False),
        sa.Column("delivery_geofence_radius_m", sa.Integer(), nullable=False),
        sa.Column("latest_latitude", sa.Float(), nullable=True),
        sa.Column("latest_longitude", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["driver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["load_id"], ["loads.id"]),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("load_id"),
    )

    op.create_table(
        "trip_status_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("trip_id", sa.String(length=36), nullable=False),
        sa.Column("status", trip_status_enum, nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("emitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("trip_id", sa.String(length=36), nullable=False),
        sa.Column("author_id", sa.String(length=36), nullable=True),
        sa.Column("message_type", sa.String(length=32), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_system_generated", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("trip_status_events")
    op.drop_table("trips")
    op.drop_table("bids")
    op.drop_table("auctions")
    op.drop_table("loads")
    op.drop_table("compliance_documents")
    op.drop_table("route_preferences")
    op.drop_table("vehicles")
    op.drop_index(op.f("ix_invite_tokens_token"), table_name="invite_tokens")
    op.drop_table("invite_tokens")
    op.drop_table("users")
    op.drop_table("companies")

    bind = op.get_bind()
    enum_types = [
        trip_status_enum,
        bid_status_enum,
        auction_mode_enum,
        load_status_enum,
        document_status_enum,
        document_type_enum,
        vehicle_kind_enum,
        user_role_enum,
    ]
    for enum_type in enum_types:
        enum_type.drop(bind, checkfirst=True)
