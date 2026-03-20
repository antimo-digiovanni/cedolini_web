from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps.auth import get_current_user, get_db, require_roles
from app.core.security import create_access_token, create_refresh_token
from app.models.domain import Company, User, UserRole
from app.schemas.auth import (
    AuthResponse,
    CarrierRegistrationRequest,
    CompanyResponse,
    DriverRegistrationRequest,
    InviteCreateRequest,
    InviteResponse,
    LoginRequest,
    MeResponse,
    TokenPairResponse,
    UserResponse,
)
from app.services.auth import (
    authenticate_user,
    create_carrier_owner,
    create_driver_from_invite,
    email_exists,
    generate_invite,
    get_active_invite,
    vat_number_exists,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register/carrier", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register_carrier(
    payload: CarrierRegistrationRequest,
    session: Session = Depends(get_db),
) -> AuthResponse:
    if email_exists(session, payload.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    if vat_number_exists(session, payload.vat_number):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="VAT number already registered")

    company, user = create_carrier_owner(
        session,
        company_name=payload.company_name,
        vat_number=payload.vat_number,
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone_number=payload.phone_number,
    )
    return _build_auth_response(user, company)


@router.post("/register/driver", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register_driver(
    payload: DriverRegistrationRequest,
    session: Session = Depends(get_db),
) -> AuthResponse:
    if email_exists(session, payload.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    invite = get_active_invite(session, payload.invite_token)
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite token not valid")

    user = create_driver_from_invite(
        session,
        invite=invite,
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone_number=payload.phone_number,
    )
    company = session.get(Company, user.company_id) if user.company_id else None
    return _build_auth_response(user, company)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, session: Session = Depends(get_db)) -> AuthResponse:
    user = authenticate_user(session, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    company = session.get(Company, user.company_id) if user.company_id else None
    return _build_auth_response(user, company)


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user), session: Session = Depends(get_db)) -> MeResponse:
    company = session.get(Company, current_user.company_id) if current_user.company_id else None
    return MeResponse(user=_to_user_response(current_user), company=_to_company_response(company))


@router.post("/invites", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
def create_invite(
    payload: InviteCreateRequest,
    current_user: User = Depends(require_roles(UserRole.carrier_owner, UserRole.dispatcher, UserRole.admin)),
    session: Session = Depends(get_db),
) -> InviteResponse:
    if current_user.company_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current user has no company")
    if payload.role not in {UserRole.driver, UserRole.dispatcher}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invite role not allowed")

    invite = generate_invite(
        session,
        company_id=current_user.company_id,
        role=payload.role,
        created_by_user_id=current_user.id,
        validity_hours=payload.validity_hours,
    )
    return InviteResponse(
        id=invite.id,
        token=invite.token,
        role=invite.role,
        is_active=invite.is_active,
        expires_at=invite.expires_at,
    )


def _build_auth_response(user: User, company: Optional[Company]) -> AuthResponse:
    access_token = create_access_token(user.id, {"role": user.role.value, "company_id": user.company_id})
    refresh_token = create_refresh_token(user.id)
    return AuthResponse(
        tokens=TokenPairResponse(access_token=access_token, refresh_token=refresh_token),
        user=_to_user_response(user),
        company=_to_company_response(company),
    )


def _to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        company_id=user.company_id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone_number=user.phone_number,
        role=user.role,
        is_active=user.is_active,
    )


def _to_company_response(company: Optional[Company]) -> Optional[CompanyResponse]:
    if company is None:
        return None
    return CompanyResponse(
        id=company.id,
        legal_name=company.legal_name,
        vat_number=company.vat_number,
        compliance_blocked=company.compliance_blocked,
    )
