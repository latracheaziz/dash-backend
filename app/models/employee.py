"""
Employee SQLAlchemy model.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    department = Column(String(255), nullable=True, default="")
    position = Column(String(255), nullable=True, default="")
    salary = Column(Float, nullable=True, default=0.0)
    phone = Column(String(50), nullable=True, default="")
    status = Column(String(50), nullable=False, default="active")
    hashed_password = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())