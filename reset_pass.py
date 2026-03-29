import sys
import os

from backend.database import SessionLocal, User
from backend.auth import hash_password

db = SessionLocal()
users = db.query(User).filter(User.name.ilike('%Anna%')).all()

if not users:
    print("No user found with name containing 'Anna'")
else:
    for u in users:
        print(f"Found User: {u.name} (Mobile: {u.mobile}, Role: {u.role})")
        u.hashed_pw = hash_password("123456")
    db.commit()
    print("Password reset to '123456' for the above user(s).")

db.close()
