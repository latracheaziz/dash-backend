"""
Standalone script to manually create/verify the super admin user.
The super admin is also auto-seeded on application startup.
"""

from app.database import Base, engine, SessionLocal
from app.models.user import User  # noqa: F401
from app.services.user_service import create_user, get_user_by_email
from app.core.config import settings


def main():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        admin = get_user_by_email(db, settings.SUPER_ADMIN_EMAIL)
        if admin:
            print(f"✓ Super admin already exists ({admin.email}, role={admin.role})")
        else:
            user = create_user(
                db,
                email=settings.SUPER_ADMIN_EMAIL,
                password=settings.SUPER_ADMIN_PASSWORD,
                role="super_admin",
                full_name="Super Admin",
            )
            print("✓ Super admin created successfully")
            print(f"  Email: {user.email}")
            print(f"  Role:  {user.role}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
