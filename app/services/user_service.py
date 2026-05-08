"""
User service — business logic for user operations.
"""

from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import hash_password


def get_user_by_email(db: Session, email: str) -> User | None:
    """Retrieve a user by email address."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Retrieve a user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def create_user(
    db: Session,
    email: str,
    password: str,
    role: str = "user",
    full_name: str | None = None,
) -> User:
    """Create a new user with a hashed password."""
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user