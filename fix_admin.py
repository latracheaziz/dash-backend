from app.database import SessionLocal
from app.models.user import User
from app.core.security import hash_password

db = SessionLocal()
admin = db.query(User).filter(User.email == 'azizlatrache5@gmail.com').first()
if admin:
    admin.hashed_password = hash_password('aziz1234')
    db.commit()
    print("Admin password forcefully updated to aziz1234")
else:
    print("Admin user not found!")
db.close()
