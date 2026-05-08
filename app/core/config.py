"""
Application configuration.
Centralizes all settings and environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ─── Application ────────────────────────────────────────────
    APP_TITLE: str = "Employee Management API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = (
        "FastAPI backend with JWT auth, role-based access, and employee management"
    )

    # ─── Database ───────────────────────────────────────────────
    BASE_DIR: str = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'db.sqlite3')}"
    )

    # ─── JWT ────────────────────────────────────────────────────
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", "f7a3b9c1d4e8f2a6b0c5d9e3f1a7b4c8d2e6f0a3b7c1d5e9f2a8b3c7d0e4f6"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120")
    )

    # ─── CORS ───────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ]

    # ─── Super Admin Seed ───────────────────────────────────────
    SUPER_ADMIN_EMAIL: str = os.getenv("SUPER_ADMIN_EMAIL", "azizlatrache5@gmail.com")
    SUPER_ADMIN_PASSWORD: str = os.getenv("SUPER_ADMIN_PASSWORD", "aziz1234")


settings = Settings()
