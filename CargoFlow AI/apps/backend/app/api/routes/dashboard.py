from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps.auth import get_current_user, get_db, require_roles
from app.models.domain import (
    Auction,
    Bid,
    ChatMessage,
    Company,
    ComplianceDocument,
    DocumentStatus,
    Load,
    LoadStatus,
    Trip,
    TripStatus,
    TripStatusEvent,
    User,
    UserRole,
)
from app.schemas.dashboard import (
    CarrierDashboardResponse,
    DriverDashboardResponse,
    MetricCardResponse,
    TimelineItemResponse,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/carrier", response_model=CarrierDashboardResponse)
def carrier_dashboard(
    current_user: User = Depends(require_roles(UserRole.carrier_owner, UserRole.dispatcher, UserRole.admin)),
    session: Session = Depends(get_db),
) -> CarrierDashboardResponse:
    now = datetime.utcnow()
    company = session.get(Company, current_user.company_id) if current_user.company_id else None
    company_label = company.legal_name if company else "Azienda"
    open_loads_count = _count_company_open_loads(session, current_user.company_id)
    live_auctions_count = _count_company_live_auctions(session, current_user.company_id, now)
    compliance_score = _build_compliance_score(session, company, now)
    active_loads = _build_carrier_active_loads(session, current_user.company_id, company_label)
    live_auctions = _build_carrier_live_auctions(session, current_user.company_id, now)
    compliance = _build_carrier_compliance(session, current_user.company_id, now)

    return CarrierDashboardResponse(
        metrics=[
            MetricCardResponse(label="Carichi aperti", value=str(open_loads_count), tone="ember"),
            MetricCardResponse(label="Aste live", value=str(live_auctions_count), tone="pine"),
            MetricCardResponse(label="Compliance score", value=compliance_score, tone="sky"),
        ],
        active_loads=active_loads,
        live_auctions=live_auctions,
        compliance=compliance,
    )


@router.get("/driver", response_model=DriverDashboardResponse)
def driver_dashboard(
    current_user: User = Depends(require_roles(UserRole.driver)),
    session: Session = Depends(get_db),
) -> DriverDashboardResponse:
    now = datetime.utcnow()
    company = session.get(Company, current_user.company_id) if current_user.company_id else None
    driver_name = f"{current_user.first_name} {current_user.last_name}"
    company_label = company.legal_name if company else "Azienda"
    active_trips = _get_driver_active_trips(session, current_user.id)
    geofence_events_today = _count_driver_geofence_events_today(session, current_user.id, now)
    pending_documents = _count_driver_pending_documents(session, current_user.id)

    return DriverDashboardResponse(
        metrics=[
            MetricCardResponse(label="Missioni attive", value=str(len(active_trips)), tone="pine"),
            MetricCardResponse(
                label="Check-in geofence",
                value=f"{geofence_events_today}/{max(len(active_trips), 1)}",
                tone="sky",
            ),
            MetricCardResponse(label="Documenti da caricare", value=str(pending_documents), tone="ember"),
        ],
        assigned_trips=_build_driver_assigned_trips(active_trips, driver_name, company_label),
        today_checklist=_build_driver_checklist(session, current_user.id, active_trips),
        alerts=_build_driver_alerts(session, current_user.id, active_trips, now),
    )


@router.get("/me")
def dashboard_me(current_user: User = Depends(get_current_user)) -> dict[str, str]:
    if current_user.role == UserRole.driver:
        return {"role": "driver", "recommended_endpoint": "/api/dashboard/driver"}
    if current_user.role in {UserRole.carrier_owner, UserRole.dispatcher, UserRole.admin}:
        return {"role": current_user.role.value, "recommended_endpoint": "/api/dashboard/carrier"}
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported role")


def _count_company_open_loads(session: Session, company_id: Optional[str]) -> int:
    if not company_id:
        return 0
    return (
        session.query(func.count(Load.id))
        .filter(
            Load.company_id == company_id,
            Load.status.in_([LoadStatus.open, LoadStatus.auction_live, LoadStatus.assigned]),
        )
        .scalar()
        or 0
    )


def _count_company_live_auctions(session: Session, company_id: Optional[str], now: datetime) -> int:
    if not company_id:
        return 0
    return (
        session.query(func.count(Auction.id))
        .join(Load, Auction.load_id == Load.id)
        .filter(
            Load.company_id == company_id,
            Auction.is_closed.is_(False),
            Auction.ends_at >= now,
        )
        .scalar()
        or 0
    )


def _build_compliance_score(session: Session, company: Optional[Company], now: datetime) -> str:
    if not company:
        return "0/100"

    documents = (
        session.query(ComplianceDocument)
        .filter(ComplianceDocument.company_id == company.id)
        .all()
    )
    if not documents:
        return "70/100"

    healthy_documents = 0
    for document in documents:
        if document.status == DocumentStatus.valid and (document.expires_at is None or document.expires_at >= now):
            healthy_documents += 1

    ratio = healthy_documents / len(documents)
    base_score = int(ratio * 100)
    if company.compliance_blocked:
        base_score = max(base_score - 35, 0)
    return f"{base_score}/100"


def _build_carrier_active_loads(session: Session, company_id: Optional[str], company_label: str) -> list[TimelineItemResponse]:
    if not company_id:
        return [_empty_item("load-empty", "Nessun carico attivo", "Crea il primo carico per attivare il matching", "La dashboard si aggiornera automaticamente.")]

    loads = (
        session.query(Load)
        .options(joinedload(Load.preferred_vehicle))
        .filter(
            Load.company_id == company_id,
            Load.status.in_([LoadStatus.open, LoadStatus.auction_live, LoadStatus.assigned]),
        )
        .order_by(Load.pickup_window_start.asc())
        .limit(3)
        .all()
    )
    if not loads:
        return [_empty_item("load-empty", "Nessun carico attivo", f"{company_label} non ha ancora carichi pubblicati", "Pubblica un carico per vedere il funnel operativo.")]

    return [
        TimelineItemResponse(
            id=load.id,
            title=f"{load.code} | {load.origin_label} -> {load.destination_label}",
            subtitle=f"Partenza {load.pickup_window_start.strftime('%d/%m %H:%M')} · consegna entro {load.delivery_window_end.strftime('%d/%m %H:%M')}",
            meta=_build_load_meta(load),
            status=_map_load_status(load.status),
        )
        for load in loads
    ]


def _build_carrier_live_auctions(session: Session, company_id: Optional[str], now: datetime) -> list[TimelineItemResponse]:
    if not company_id:
        return [_empty_item("auction-empty", "Nessuna asta attiva", "Attiva un'asta su un carico per ricevere offerte", "Le migliori offerte compariranno qui.")]

    auctions = (
        session.query(Auction)
        .options(joinedload(Auction.load), joinedload(Auction.bids))
        .join(Load, Auction.load_id == Load.id)
        .filter(
            Load.company_id == company_id,
            Auction.is_closed.is_(False),
            Auction.ends_at >= now,
        )
        .order_by(Auction.ends_at.asc())
        .limit(3)
        .all()
    )
    if not auctions:
        return [_empty_item("auction-empty", "Nessuna asta attiva", "Nessuna asta live per i carichi correnti", "Promuovi un carico ad asta per aumentare la copertura.")]

    items: list[TimelineItemResponse] = []
    for auction in auctions:
        best_bid = min((bid.amount for bid in auction.bids), default=None)
        items.append(
            TimelineItemResponse(
                id=auction.id,
                title=f"Asta {auction.load.code} | {auction.load.origin_label} -> {auction.load.destination_label}",
                subtitle=f"Chiude il {auction.ends_at.strftime('%d/%m alle %H:%M')}",
                meta=_build_auction_meta(auction, best_bid),
                status="live" if auction.ends_at - now <= timedelta(hours=4) else "planned",
            )
        )
    return items


def _build_carrier_compliance(session: Session, company_id: Optional[str], now: datetime) -> list[TimelineItemResponse]:
    if not company_id:
        return [_empty_item("compliance-empty", "Compliance non disponibile", "Associa prima un'azienda a questo utente", "I documenti aziendali compariranno qui.")]

    documents = (
        session.query(ComplianceDocument)
        .filter(ComplianceDocument.company_id == company_id)
        .order_by(ComplianceDocument.expires_at.asc().nullslast(), ComplianceDocument.created_at.desc())
        .limit(3)
        .all()
    )
    if not documents:
        return [_empty_item("compliance-empty", "Nessun documento caricato", "Carica DURC, polizze e registri vettoriali", "Lo score compliance migliora quando i documenti sono validi.")]

    return [
        TimelineItemResponse(
            id=document.id,
            title=_humanize_document_type(document.document_type.value),
            subtitle=_build_document_subtitle(document, now),
            meta=_build_document_meta(document),
            status=_map_document_status(document, now),
        )
        for document in documents
    ]


def _get_driver_active_trips(session: Session, user_id: str) -> list[Trip]:
    return (
        session.query(Trip)
        .options(joinedload(Trip.load), joinedload(Trip.vehicle), joinedload(Trip.chat_messages))
        .filter(
            Trip.driver_id == user_id,
            Trip.current_status.in_(
                [
                    TripStatus.assigned,
                    TripStatus.heading_to_pickup,
                    TripStatus.arrived_at_pickup,
                    TripStatus.loaded,
                    TripStatus.in_transit,
                    TripStatus.arrived_at_delivery,
                ]
            ),
        )
        .order_by(Trip.created_at.desc())
        .limit(3)
        .all()
    )


def _count_driver_geofence_events_today(session: Session, user_id: str, now: datetime) -> int:
    start_of_day = datetime(now.year, now.month, now.day)
    return (
        session.query(func.count(TripStatusEvent.id))
        .join(Trip, TripStatusEvent.trip_id == Trip.id)
        .filter(
            Trip.driver_id == user_id,
            TripStatusEvent.emitted_at >= start_of_day,
            TripStatusEvent.status.in_([TripStatus.arrived_at_pickup, TripStatus.arrived_at_delivery]),
        )
        .scalar()
        or 0
    )


def _count_driver_pending_documents(session: Session, user_id: str) -> int:
    return (
        session.query(func.count(ComplianceDocument.id))
        .filter(
            ComplianceDocument.user_id == user_id,
            ComplianceDocument.status.in_([DocumentStatus.pending, DocumentStatus.rejected]),
        )
        .scalar()
        or 0
    )


def _build_driver_assigned_trips(
    trips: list[Trip], driver_name: str, company_label: str
) -> list[TimelineItemResponse]:
    if not trips:
        return [_empty_item("trip-empty", "Nessuna missione attiva", f"{driver_name} non ha viaggi assegnati", f"{company_label} potra assegnare una missione non appena un carico viene confermato.")]

    return [
        TimelineItemResponse(
            id=trip.id,
            title=f"Missione {trip.load.code} | {trip.load.origin_label} -> {trip.load.destination_label}",
            subtitle=f"Stato: {_humanize_trip_status(trip.current_status)} · consegna entro {trip.load.delivery_window_end.strftime('%d/%m %H:%M')}",
            meta=_build_trip_meta(trip),
            status=_map_trip_status(trip.current_status),
        )
        for trip in trips
    ]


def _build_driver_checklist(session: Session, user_id: str, trips: list[Trip]) -> list[TimelineItemResponse]:
    items: list[TimelineItemResponse] = []
    pending_documents = _count_driver_pending_documents(session, user_id)
    unread_chat_messages = _count_driver_unread_like_messages(trips)

    if trips:
        first_trip = trips[0]
        items.append(
            TimelineItemResponse(
                id=f"check-trip-{first_trip.id}",
                title="Conferma avanzamento missione",
                subtitle=f"Aggiorna {_humanize_trip_status(first_trip.current_status).lower()} per {first_trip.load.code}",
                meta="Invia posizione o cambia stato per mantenere il tracking coerente.",
                status="attention" if first_trip.current_status in {TripStatus.assigned, TripStatus.heading_to_pickup} else "planned",
            )
        )

    items.append(
        TimelineItemResponse(
            id="check-documents",
            title="Documentazione operativa",
            subtitle=f"{pending_documents} documenti da completare",
            meta="Carica CMR, DDT o patente aggiornata per sbloccare i passaggi successivi.",
            status="attention" if pending_documents else "planned",
        )
    )
    items.append(
        TimelineItemResponse(
            id="check-chat",
            title="Chat operativa",
            subtitle=f"{unread_chat_messages} messaggi recenti sulle missioni attive",
            meta="Le chat di viaggio restano il punto di contatto con il disponente.",
            status="live" if unread_chat_messages else "planned",
        )
    )
    return items[:3]


def _build_driver_alerts(session: Session, user_id: str, trips: list[Trip], now: datetime) -> list[TimelineItemResponse]:
    alerts: list[TimelineItemResponse] = []

    expiring_documents = (
        session.query(ComplianceDocument)
        .filter(
            ComplianceDocument.user_id == user_id,
            ComplianceDocument.expires_at.is_not(None),
            ComplianceDocument.expires_at <= now + timedelta(days=14),
        )
        .order_by(ComplianceDocument.expires_at.asc())
        .limit(2)
        .all()
    )
    for document in expiring_documents:
        alerts.append(
            TimelineItemResponse(
                id=f"alert-doc-{document.id}",
                title=f"Documento in scadenza: {_humanize_document_type(document.document_type.value)}",
                subtitle=_build_document_subtitle(document, now),
                meta="Aggiorna il documento per evitare blocchi sulle nuove assegnazioni.",
                status="attention",
            )
        )
    for trip in trips:
        if trip.load.delivery_window_end <= now + timedelta(hours=2):
            alerts.append(
                TimelineItemResponse(
                    id=f"alert-trip-{trip.id}",
                    title=f"Consegna vicina per {trip.load.code}",
                    subtitle=f"Deadline {trip.load.delivery_window_end.strftime('%d/%m %H:%M')}",
                    meta="Verifica geofence e prova di consegna prima della finestra finale.",
                    status="attention",
                )
            )

    if alerts:
        return alerts[:3]
    return [_empty_item("alert-empty", "Nessun alert urgente", "Missioni e documenti sono sotto controllo", "Qui compariranno ritardi, scadenze o anomalie operative.")]


def _build_load_meta(load: Load) -> str:
    parts = []
    if load.budget_amount is not None:
        parts.append(f"Budget {load.budget_amount:,.0f} EUR".replace(",", "."))
    parts.append(load.vehicle_kind.value.replace("_", " "))
    if load.adr_required:
        parts.append("ADR richiesto")
    if load.preferred_vehicle and load.preferred_vehicle.plate_number:
        parts.append(f"Mezzo {load.preferred_vehicle.plate_number}")
    return " · ".join(parts)


def _build_auction_meta(auction: Auction, best_bid: Optional[float]) -> str:
    parts = []
    if auction.floor_price is not None:
        parts.append(f"Base {auction.floor_price:,.0f} EUR".replace(",", "."))
    if best_bid is not None:
        parts.append(f"Miglior offerta {best_bid:,.0f} EUR".replace(",", "."))
    parts.append(f"{len(auction.bids)} offerte")
    return " · ".join(parts)


def _build_document_subtitle(document: ComplianceDocument, now: datetime) -> str:
    if document.expires_at is None:
        return f"Stato {document.status.value}"
    delta_days = (document.expires_at - now).days
    if delta_days < 0:
        return f"Scaduto da {abs(delta_days)} giorni"
    if delta_days == 0:
        return "Scade oggi"
    return f"Scade tra {delta_days} giorni"


def _build_document_meta(document: ComplianceDocument) -> str:
    return f"Fonte documento: {document.status.value} · file registrato"


def _build_trip_meta(trip: Trip) -> str:
    parts = []
    if trip.vehicle and trip.vehicle.plate_number:
        parts.append(f"Mezzo {trip.vehicle.plate_number}")
    parts.append(f"Pickup geofence {trip.pickup_geofence_radius_m} m")
    recent_messages = len(trip.chat_messages)
    parts.append(f"Chat {recent_messages} messaggi")
    return " · ".join(parts)


def _count_driver_unread_like_messages(trips: list[Trip]) -> int:
    return sum(1 for trip in trips for message in trip.chat_messages if not message.is_system_generated)


def _humanize_document_type(document_type: str) -> str:
    mapping = {
        "durc": "DURC aziendale",
        "insurance": "Polizza assicurativa",
        "carrier_register": "Iscrizione albo vettori",
        "driving_license": "Patente di guida",
        "cmr": "CMR",
        "ddt": "DDT",
    }
    return mapping.get(document_type, document_type.replace("_", " ").title())


def _humanize_trip_status(status_value: TripStatus) -> str:
    return status_value.value.replace("_", " ")


def _map_load_status(status_value: LoadStatus) -> str:
    if status_value == LoadStatus.auction_live:
        return "live"
    if status_value == LoadStatus.assigned:
        return "planned"
    return "attention" if status_value == LoadStatus.open else "planned"


def _map_document_status(document: ComplianceDocument, now: datetime) -> str:
    if document.status in {DocumentStatus.pending, DocumentStatus.rejected}:
        return "attention"
    if document.expires_at is not None and document.expires_at <= now + timedelta(days=14):
        return "attention"
    return "planned"


def _map_trip_status(status_value: TripStatus) -> str:
    if status_value in {TripStatus.loaded, TripStatus.in_transit, TripStatus.arrived_at_delivery}:
        return "live"
    if status_value in {TripStatus.assigned, TripStatus.heading_to_pickup}:
        return "attention"
    return "planned"


def _empty_item(item_id: str, title: str, subtitle: str, meta: str) -> TimelineItemResponse:
    return TimelineItemResponse(id=item_id, title=title, subtitle=subtitle, meta=meta, status="planned")
