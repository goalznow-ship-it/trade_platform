import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Set
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_db
from app.core.logging import logger

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# JWT Blacklist (in-memory, use Redis for production)
_token_blacklist: Set[str] = set()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access", "jti": hashlib.sha256(str(datetime.now(timezone.utc).timestamp()).encode()).hexdigest()[:16]})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh", "jti": hashlib.sha256(str(datetime.now(timezone.utc).timestamp() + 1).encode()).hexdigest()[:16]})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        jti = payload.get("jti")
        if jti and jti in _token_blacklist:
            raise HTTPException(status_code=401, detail="Token revoked")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def revoke_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        jti = payload.get("jti")
        if jti:
            _token_blacklist.add(jti)
    except JWTError:
        pass


def revoke_all_user_tokens(user_id: int):
    pass


def generate_totp_secret() -> str:
    import base64, os
    return base64.b32encode(os.urandom(20)).decode()


def verify_totp(secret: str, code: str) -> bool:
    try:
        import pyotp
        totp = pyotp.TOTP(secret)
        return totp.verify(code)
    except ImportError:
        return False


def sanitize_input(value: str) -> str:
    import re
    if not value:
        return value
    value = re.sub(r"[<>\'\";&|`$]", "", value)
    return value[:1000]


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    from app.models.user import User
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(401, "Invalid token type")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "Invalid token")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")
    if user.subscription_expires and user.subscription_expires < datetime.now(timezone.utc):
        if user.subscription_tier != "free":
            user.subscription_tier = "free"
            user.subscription_expires = None
            await db.commit()
    return user


async def require_admin(user = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(403, "Admin access required")
    return user

def require_subscription(min_tier: str = "pro"):
    """Subscription permission check dependency factory."""
    async def _check(user = Depends(get_current_user)):
        tier = user.subscription_tier or "free"
        tiers = {"free": 0, "pro": 1, "elite": 2}
        required = tiers.get(min_tier, 0)
        actual = tiers.get(tier, 0)
        if actual < required:
            raise HTTPException(403, f"Subscription required: {min_tier} tier or higher")
        return user
    return _check


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith(("/docs", "/redoc", "/openapi", "/health")):
            return await call_next(request)
        response = await call_next(request)
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            logger.info(json.dumps({
                "audit": True,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", ""),
            }))
        return response
