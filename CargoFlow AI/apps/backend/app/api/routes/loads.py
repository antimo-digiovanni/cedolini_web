from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_db, require_roles
from app.models.domain import Load, LoadStatus, User, UserRole, Vehicle
from app.schemas.load import LoadCreateRequest, LoadListResponse, LoadResponse

router = APIRouter(prefix="/loads", tags=["loads"])


@router.get("", response_model=LoadListResponse)
def list_loads(
    status_filter: Optional[LoadStatus] = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.carrier_owner, UserRole.dispatcher, UserRole.admin)),
    session: Session = Depends(get_db),
) -> LoadListResponse:
    if current_user.company_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current user has no company")

    query = session.query(Load).filter(Load.company_id == current_user.company_id)
    if status_filter is not None:
        query = query.filter(Load.status == status_filter)

    loads = query.order_by(Load.created_at.desc()).limit(limit).all()
    return LoadListResponse(items=[_to_load_response(load) for load in loads], total=len(loads))


@router.get("/{load_id}", response_model=LoadResponse)
def get_load(
    load_id: str,
    current_user: User = Depends(require_roles(UserRole.carrier_owner, UserRole.dispatcher, UserRole.admin)),
    session: Session = Depends(get_db),
) -> LoadResponse:
    load = session.get(Load, load_id)
    if load is None or load.company_id != current_user.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load not found")
    return _to_load_response(load)


@router.post("", response_model=LoadResponse, status_code=status.HTTP_201_CREATED)
def create_load(
    payload: LoadCreateRequest,
    current_user: User = Depends(require_roles(UserRole.carrier_owner, UserRole.dispatcher, UserRole.admin)),
    session: Session = Depends(get_db),
) -> LoadResponse:
    if current_user.company_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current user has no company")
    if payload.delivery_window_end <= payload.pickup_window_start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Delivery window must be after pickup window")

    if payload.preferred_vehicle_id:
        vehicle = session.get(Vehicle, payload.preferred_vehicle_id)
        if vehicle is None or vehicle.company_id != current_user.company_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Preferred vehicle not valid for company")

    load = Load(
        company_id=current_user.company_id,
        preferred_vehicle_id=payload.preferred_vehicle_id,
        code=_generate_load_code(session),
        title=payload.title,
        origin_label=payload.origin_label,
        destination_label=payload.destination_label,
        pickup_window_start=payload.pickup_window_start,
        delivery_window_end=payload.delivery_window_end,
        budget_amount=payload.budget_amount,
        vehicle_kind=payload.vehicle_kind,
        adr_required=payload.adr_required,
        status=LoadStatus.open,
    )
    session.add(load)
    session.commit()
    session.refresh(load)
    return _to_load_response(load)


def _generate_load_code(session: Session) -> str:
    prefix = datetime.utcnow().strftime("LD%y%m")
    candidate_number = 1
    while True:
        candidate = f"{prefix}-{candidate_number:04d}"
        exists = session.query(Load.id).filter(Load.code == candidate).first()
        if exists is None:
            return candidate
        candidate_number += 1


def _to_load_response(load: Load) -> LoadResponse:
    return LoadResponse(
        id=load.id,
        company_id=load.company_id,
        preferred_vehicle_id=load.preferred_vehicle_id,
        code=load.code,
        title=load.title,
        origin_label=load.origin_label,
        destination_label=load.destination_label,
        pickup_window_start=load.pickup_window_start,
        delivery_window_end=load.delivery_window_end,
        budget_amount=load.budget_amount,
        vehicle_kind=load.vehicle_kind,
        adr_required=load.adr_required,
        status=load.status,
        created_at=load.created_at,
    )