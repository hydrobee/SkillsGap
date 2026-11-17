from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models import User

ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(user_id: int, hours: int = 8) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=hours)
    return jwt.encode({"sub": str(user_id), "exp": exp},
                      settings.secret_key, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme),
                     db: Session = Depends(get_db)) -> User:
    err = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise err
    if user is None:
        raise err
    return user


def require_role(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")
        return user
    return checker


def can_view_user(viewer: User, target: User) -> bool:
    """staff: self only | supervisor: self + direct reports | hr: everyone."""
    if viewer.role == "hr" or viewer.id == target.id:
        return True
    return viewer.role == "supervisor" and target.supervisor_id == viewer.id


def assert_can_view(viewer: User, target: User) -> None:
    if not can_view_user(viewer, target):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot view this user")