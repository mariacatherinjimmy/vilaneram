# backend/auth.py
# ============================================================
# VilaNeram 2.0 — JWT Authentication
# Roles: farmer | shopkeeper | admin
# ============================================================

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .database import get_db, User

SECRET_KEY  = os.getenv("SECRET_KEY", "vilaneram2-secret-key-2025")
ALGORITHM   = os.getenv("ALGORITHM", "HS256")
EXPIRE_MINS = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours

pwd_ctx  = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer   = HTTPBearer()


def hash_password(pw: str) -> str:
    return pwd_ctx.hash(pw)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=EXPIRE_MINS)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _get_user_from_token(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db)
) -> User:
    token = creds.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token.")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token expired or invalid.")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated.")
    return user


def get_current_user(user: User = Depends(_get_user_from_token)) -> User:
    return user


def require_farmer(user: User = Depends(_get_user_from_token)) -> User:
    if user.role not in ("farmer", "admin"):
        raise HTTPException(status_code=403, detail="Farmer access required.")
    return user


def require_shopkeeper(user: User = Depends(_get_user_from_token)) -> User:
    if user.role not in ("shopkeeper", "admin"):
        raise HTTPException(status_code=403, detail="Shopkeeper access required.")
    return user


def require_admin(user: User = Depends(_get_user_from_token)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user