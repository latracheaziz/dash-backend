"""
Pydantic schemas for Employee CRUD.
"""

from pydantic import BaseModel, EmailStr
from datetime import datetime


# ─── Request Schemas ────────────────────────────────────────

class EmployeeCreate(BaseModel):
    """Schema for creating an employee."""
    name: str
    email: EmailStr
    department: str | None = ""
    position: str | None = ""
    salary: float | None = 0.0
    phone: str | None = ""
    status: str | None = "active"
    password: str | None = None


class EmployeeUpdate(BaseModel):
    """Schema for updating an employee. All fields optional for partial updates."""
    name: str | None = None
    email: EmailStr | None = None
    department: str | None = None
    position: str | None = None
    salary: float | None = None
    phone: str | None = None
    status: str | None = None


# ─── Response Schemas ───────────────────────────────────────

class EmployeeOut(BaseModel):
    """Schema for employee responses."""
    id: int
    name: str
    email: str
    department: str | None = ""
    position: str | None = ""
    salary: float | None = 0.0
    phone: str | None = ""
    status: str = "active"
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True