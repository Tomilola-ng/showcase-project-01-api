"""Accounts Auth"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Header
from tortoise.exceptions import OperationalError

from app.config.settings import settings
from app.accounts.models import Account

# --- Security constants ---
SECRET_KEY = settings.API_AUTHORIZATION_TOKEN
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30
REFRESH_TOKEN_EXPIRE_DAYS = 70

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# --- Password Utils ---
def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# --- JWT Utils ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "scope": "access_token"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    expire = datetime.now(timezone.utc) + \
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {**data, "exp": expire, "scope": "refresh_token"}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode a JWT and validate its signature."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def decode_refresh_token(token: str) -> dict:
    """Decode a JWT refresh token and validate its signature and scope."""
    payload = decode_token(token)
    if payload.get("scope") != "refresh_token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token scope",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


# --- User retrieval ---
async def get_user_from_token(token: str) -> Optional[Account]:
    """Retrieve a user object from a JWT token with DB error handling."""
    payload = decode_token(token)
    if payload.get("scope") != "access_token":
        raise HTTPException(status_code=401, detail="Invalid token scope")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user ID in token")

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user ID format")

    # DB access wrapped with error handling
    try:
        user = await Account.filter(id=user_uuid).first()
    except OperationalError:
        raise HTTPException(
            status_code=500, detail="Database connection error")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


# --- Current user dependency ---
async def get_current_user(authorization: Optional[str] = Header(None)) -> Account:
    """Resolve current user from Authorization header.
    Supports `JWT <token>` and falls back to `Bearer <token>` for tooling.
    """
    if not authorization:
        raise HTTPException(
            status_code=401, detail="Missing authorization header")

    token: Optional[str] = None
    if authorization.startswith("JWT "):
        token = authorization[4:]
    elif authorization.startswith("Bearer "):
        parts = authorization.split()
        if len(parts) == 2:
            token = parts[1]

    if not token:
        raise HTTPException(
            status_code=401, detail="Invalid authorization scheme")

    return await get_user_from_token(token)


async def get_current_user_optional(authorization: Optional[str] = Header(None)) -> Optional[Account]:
    """Resolve current user from Authorization header, returns None if not authenticated.
    Supports `JWT <token>` and falls back to `Bearer <token>` for tooling.
    """
    if not authorization:
        return None

    token: Optional[str] = None
    if authorization.startswith("JWT "):
        token = authorization[4:]
    elif authorization.startswith("Bearer "):
        parts = authorization.split()
        if len(parts) == 2:
            token = parts[1]

    if not token:
        return None

    try:
        return await get_user_from_token(token)
    except HTTPException:
        return None
