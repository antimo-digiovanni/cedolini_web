from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps.auth import get_db, require_roles
from app.models.domain import Auction, Load, LoadStatus, User, UserRole
from app.schemas.auction import AuctionCreateRequest, AuctionListResponse, AuctionResponse

router = APIRouter(prefix="/auctions", tags=["auctions"])


@router.get("", response_model=AuctionListResponse)
def list_auctions(
    live_only: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.carrier_owner, UserRole.dispatcher, UserRole.admin)),
    session: Session = Depends(get_db),
) -> AuctionListResponse:
    if current_user.company_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current user has no company")

    query = (
        session.query(Auction)
        .options(joinedload(Auction.load))
        .join(Load, Auction.load_id == Load.id)
        .filter(Load.company_id == current_user.company_id)
    )
    if live_only:
        now = datetime.utcnow()
        query = query.filter(Auction.is_closed.is_(False), Auction.ends_at >= now)

    items = query.order_by(Auction.created_at.desc()).limit(limit).all()
    return AuctionListResponse(items=[_to_auction_response(item) for item in items], total=len(items))


@router.get("/{auction_id}", response_model=AuctionResponse)
def get_auction(
    auction_id: str,
    current_user: User = Depends(require_roles(UserRole.carrier_owner, UserRole.dispatcher, UserRole.admin)),
    session: Session = Depends(get_db),
) -> AuctionResponse:
    auction = (
        session.query(Auction)
        .options(joinedload(Auction.load))
        .filter(Auction.id == auction_id)
        .first()
    )
    if auction is None or auction.load.company_id != current_user.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auction not found")
    return _to_auction_response(auction)


@router.post("", response_model=AuctionResponse, status_code=status.HTTP_201_CREATED)
def create_auction(
    payload: AuctionCreateRequest,
    current_user: User = Depends(require_roles(UserRole.carrier_owner, UserRole.dispatcher, UserRole.admin)),
    session: Session = Depends(get_db),
) -> AuctionResponse:
    if current_user.company_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current user has no company")
    if not payload.load_id and not payload.load_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Load id or load code is required")
    if payload.ends_at <= payload.starts_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Auction end must be after start")
    if payload.floor_price is not None and payload.ceiling_price is not None and payload.floor_price > payload.ceiling_price:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Floor price cannot exceed ceiling price")

    load = _resolve_load(session, current_user.company_id, payload)
    if load is None or load.company_id != current_user.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load not found")
    if load.trip is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Load already assigned to a trip")

    existing = session.query(Auction).filter(Auction.load_id == load.id).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Auction already exists for this load")
    if load.status in {LoadStatus.cancelled, LoadStatus.completed}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Load status not compatible with auction")

    auction = Auction(
        load_id=load.id,
        mode=payload.mode,
        floor_price=payload.floor_price,
        ceiling_price=payload.ceiling_price,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        is_closed=False,
    )
    load.status = LoadStatus.auction_live
    session.add(auction)
    session.commit()
    session.refresh(auction)
    auction = (
        session.query(Auction)
        .options(joinedload(Auction.load))
        .filter(Auction.id == auction.id)
        .first()
    )
    return _to_auction_response(auction)


def _to_auction_response(auction: Auction) -> AuctionResponse:
    return AuctionResponse(
        id=auction.id,
        load_id=auction.load_id,
        load_code=auction.load.code,
        load_title=auction.load.title,
        mode=auction.mode,
        floor_price=auction.floor_price,
        ceiling_price=auction.ceiling_price,
        starts_at=auction.starts_at,
        ends_at=auction.ends_at,
        is_closed=auction.is_closed,
        created_at=auction.created_at,
    )


def _resolve_load(session: Session, company_id: str, payload: AuctionCreateRequest) -> Optional[Load]:
    if payload.load_id:
        load = session.get(Load, payload.load_id)
        if load is not None and load.company_id == company_id:
            return load
    if payload.load_code:
        return (
            session.query(Load)
            .filter(Load.company_id == company_id, Load.code == payload.load_code)
            .first()
        )
    return None