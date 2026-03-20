import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.domain import Company, InviteToken, User, UserRole


def authenticate_user(session: Session, email: str, password: str) -> Optional[User]:
    user = session.scalar(select(User).where(User.email == email.lower().strip()))
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_carrier_owner(
    session: Session,
    *,
    company_name: str,
    vat_number: str,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    phone_number: Optional[str],
) -> tuple[Company, User]:
    company = Company(
        legal_name=company_name.strip(),
        vat_number=vat_number.strip(),
    )
    user = User(
        company=company,
        email=email.lower().strip(),
        password_hash=hash_password(password),
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        phone_number=phone_number.strip() if phone_number else None,
        role=UserRole.carrier_owner,
    )
    session.add(company)
    session.add(user)
    session.commit()
    session.refresh(company)
    session.refresh(user)
    return company, user


def create_driver_from_invite(
    session: Session,
    *,
    invite: InviteToken,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    phone_number: Optional[str],
) -> User:
    user = User(
        company_id=invite.company_id,
        email=email.lower().strip(),
        password_hash=hash_password(password),
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        phone_number=phone_number.strip() if phone_number else None,
        role=invite.role,
    )
    invite.used_at = datetime.now(timezone.utc)
    invite.is_active = False
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def generate_invite(
    session: Session,
    *,
    company_id: str,
    role: UserRole,
    created_by_user_id: Optional[str],
    validity_hours: int,
) -> InviteToken:
    token = _build_unique_token(session)
    invite = InviteToken(
        company_id=company_id,
        created_by_user_id=created_by_user_id,
        token=token,
        role=role,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=validity_hours),
    )
    session.add(invite)
    session.commit()
    session.refresh(invite)
    return invite


def get_active_invite(session: Session, token: str) -> Optional[InviteToken]:
    invite = session.scalar(select(InviteToken).where(InviteToken.token == token.strip().upper()))
    if invite is None or not invite.is_active:
        return None
    if invite.expires_at is not None and invite.expires_at < datetime.now(timezone.utc):
        return None
    return invite


def email_exists(session: Session, email: str) -> bool:
    return session.scalar(select(User.id).where(User.email == email.lower().strip())) is not None


def vat_number_exists(session: Session, vat_number: str) -> bool:
    return session.scalar(select(Company.id).where(Company.vat_number == vat_number.strip())) is not None


def _build_unique_token(session: Session) -> str:
    while True:
        candidate = secrets.token_hex(4).upper()
        exists = session.scalar(select(InviteToken.id).where(InviteToken.token == candidate))
        if exists is None:
            return candidate
