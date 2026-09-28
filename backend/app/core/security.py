from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt

# Ensure compatibility between modern bcrypt (>=4.0) and passlib
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type("about", (), {"__version__": getattr(bcrypt, "__version__", "4.0.0")})()
_orig_hashpw = bcrypt.hashpw
bcrypt.hashpw = lambda p, s: _orig_hashpw(p[:72] if isinstance(p, (bytes, bytearray)) else p, s)

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_otp_hash(plain_otp: str, hashed_otp: str) -> bool:
    return pwd_context.verify(plain_otp, hashed_otp)

def get_otp_hash(otp: str) -> str:
    return pwd_context.hash(otp)

def create_access_token(
    subject: str | Any,
    role: str,
    employee_id: str | None = None,
    expires_delta: timedelta | None = None
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "role": role
    }
    if employee_id:
        to_encode["employee_id"] = str(employee_id)
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

import secrets


def create_refresh_token(subject: str | Any) -> str:
    # Opaque token
    return secrets.token_urlsafe(32)

def get_token_hash(token: str) -> str:
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()
