"""
Pydantic schemas for User authentication.
"""

from pydantic import BaseModel, EmailStr
from datetime import datetime


# ─── Request Schemas ────────────────────────────────────────

class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str
    full_name: str | None = None


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


# ─── Response Schemas ───────────────────────────────────────

class UserOut(BaseModel):
    """Schema for user responses (never exposes password hash)."""
    id: int
    email: str
    full_name: str | None = None
    role: str
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for login response."""
    access_token: str
    token_type: str = "bearer"
    user: UserOut