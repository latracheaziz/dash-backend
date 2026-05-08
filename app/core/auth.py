"""
JWT token creation and verification.
"""

from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from app.core.config import settings


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token with an expiration claim."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token. Raises JWTError on failure."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])