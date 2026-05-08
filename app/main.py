"""
FastAPI application entry point.

- Creates database tables on startup
- Seeds the super admin user
- Configures CORS for React frontend
- Registers all route modules
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine, SessionLocal
from app.core.config import settings
from app.models.user import User  # noqa: F401 — ensures table is registered
from app.models.employee import Employee  # noqa: F401 — ensures table is registered
from app.models.call_record import CallRecord  # noqa: F401 — ensures table is registered
from app.routes import auth, employee, calls

logger = logging.getLogger(__name__)


def seed_super_admin() -> None:
    """Create the default super admin user if it doesn't already exist."""
    from app.services.user_service import get_user_by_email, create_user

    db = SessionLocal()
    try:
        existing = get_user_by_email(db, settings.SUPER_ADMIN_EMAIL)
        if existing:
            logger.info("Super admin already exists — skipping seed")
            return

        create_user(
            db,
            email=settings.SUPER_ADMIN_EMAIL,
            password=settings.SUPER_ADMIN_PASSWORD,
            role="super_admin",
            full_name="Super Admin",
        )
        logger.info("Super admin seeded successfully (%s)", settings.SUPER_ADMIN_EMAIL)
    except Exception as e:
        logger.error("Failed to seed super admin: %s", e)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    # ── Startup ─────────────────────────────────────────────
    Base.metadata.create_all(bind=engine)
    seed_super_admin()
    logger.info("Application started — tables created, admin seeded")
    yield
    # ── Shutdown ────────────────────────────────────────────
    logger.info("Application shutting down")


app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan,
)

# ─── CORS Middleware ────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(employee.router)
app.include_router(calls.router)


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": settings.APP_VERSION}