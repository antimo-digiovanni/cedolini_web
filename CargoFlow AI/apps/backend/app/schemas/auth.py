from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.domain import UserRole


class CarrierRegistrationRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=160)
    vat_number: str = Field(min_length=8, max_length=32)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    phone_number: Optional[str] = Field(default=None, max_length=32)


class DriverRegistrationRequest(BaseModel):
    invite_token: str = Field(min_length=4, max_length=32)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    phone_number: Optional[str] = Field(default=None, max_length=32)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class CompanyResponse(BaseModel):
    id: str
    legal_name: str
    vat_number: str
    compliance_blocked: bool


class UserResponse(BaseModel):
    id: str
    company_id: Optional[str]
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: Optional[str]
    role: UserRole
    is_active: bool


class AuthResponse(BaseModel):
    tokens: TokenPairResponse
    user: UserResponse
    company: Optional[CompanyResponse]


class InviteCreateRequest(BaseModel):
    role: UserRole = UserRole.driver
    validity_hours: int = Field(default=72, ge=1, le=24 * 30)


class InviteResponse(BaseModel):
    id: str
    token: str
    role: UserRole
    is_active: bool
    expires_at: Optional[datetime]


class MeResponse(BaseModel):
    user: UserResponse
    company: Optional[CompanyResponse]
