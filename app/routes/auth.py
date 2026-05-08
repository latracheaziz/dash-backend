"""
Authentication routes — register, login, and current user profile.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserLogin, UserOut, TokenResponse
from app.services.user_service import create_user, get_user_by_email
from app.core.security import verify_password
from app.core.auth import create_access_token
from app.deps import get_db, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.

    - Validates email uniqueness
    - Hashes password before storing
    - Returns user data (never the password hash)
    """
    existing = get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists",
        )

    user = create_user(
        db,
        email=data.email,
        password=data.password,
        full_name=data.full_name,
    )
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get JWT token",
)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate a user and return a JWT access token.

    - Validates credentials
    - Returns token + user info for the frontend
    """
    logger.info(f"Login attempt for email: {data.email}")
    user = get_user_by_email(db, data.email)

    if not user:
        logger.warning(f"Login failed: User not found for email ({data.email})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    logger.info(f"User found in DB for email: {data.email}")

    if not verify_password(data.password, user.hashed_password):
        logger.warning(f"Login failed: Incorrect password for email ({data.email})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    logger.info(f"Login successful for email: {data.email}")

    access_token = create_access_token(data={"sub": user.email, "role": user.role})

    return TokenResponse(
        access_token=access_token,
        user=UserOut.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get current user profile",
)
def get_me(current_user=Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user