"""Accounts schemas"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from tortoise.contrib.pydantic import pydantic_model_creator
from pydantic import BaseModel, EmailStr, Field

from app.accounts.models import Account
from app.base.schemas import FileOut
from app.config.pagination import PaginatedResponse


# Account Schemas
AccountFullPydantic = pydantic_model_creator(
    Account, name="AccountFull", exclude=("password",))
AccountCreatePydantic = pydantic_model_creator(
    Account,
    name="AccountCreate",
    exclude_readonly=True,
    include=("first_name", "last_name", "email", "password"),
)


class AccountRead(BaseModel):
    """Account read schema."""
    id: UUID
    first_name: str
    last_name: str
    role: str
    email: str
    status: str
    country: str
    created_at: datetime
    state: Optional[str] = None
    image: Optional[FileOut] = None

    class Config:
        """Pydantic model configuration"""
        from_attributes = True


class AccountAdminDetail(AccountFullPydantic):
    """Admin detailed account view with image"""
    image: Optional[FileOut] = None

    class Config:
        """Pydantic config"""
        from_attributes = True


class AccountListResponse(PaginatedResponse[AccountRead]):
    """Schema for list response"""
    pass


class LoginUserSchema(BaseModel):
    """User login credentials."""
    email: EmailStr
    password: str


class EmailVerificationSchema(BaseModel):
    """Email + OTP for verification."""
    email: EmailStr
    otp_code: Optional[str] = Field(None, max_length=6)


class ForgetPasswordSchema(BaseModel):
    """Email to request password reset."""
    email: EmailStr


class ValidatePasswordSchema(BaseModel):
    """Single password field for validation."""
    password: str


class NewPasswordSchema(BaseModel):
    """Reset password with OTP."""
    email: EmailStr
    new_password: str
    confirm_password: str
    otp_code: Optional[str] = Field(None, max_length=6)


class ChangePasswordSchema(BaseModel):
    """Change password with Old Password."""
    old_password: str
    new_password: str
    confirm_password: str


class AccountUpdate(BaseModel):
    """Schema for updating user profile."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=255)
    last_name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone_number: Optional[str] = Field(None, min_length=1, max_length=255)
    country: Optional[str] = None
    state: Optional[str] = Field(None, min_length=1, max_length=255)
