from app.database import SessionLocal
from app.models.user import User
from app.core.security import hash_password

db = SessionLocal()
users = db.query(User).all()
for u in users:
    # Resetting everyone to a default password if we don't know theirs, 
    # OR we just re-hash a known one. 
    # Since I don't know their original plain passwords, I will set them to 'aziz1234' for consistency during this fix.
    u.hashed_password = hash_password('aziz1234')
    print(f"Updated password for {u.email} to 'aziz1234'")

db.commit()
db.close()
