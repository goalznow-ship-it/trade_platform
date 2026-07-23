import json
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Set
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_db
from app.core.logging import logger
from app.core.redis import redis_client

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
    to_encode.update({"exp": expire, "type": "access", "jti": secrets.token_urlsafe(24)})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh", "jti": secrets.token_urlsafe(24)})
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


async def is_token_revoked(payload: dict) -> bool:
    jti = payload.get("jti")
    if not jti:
        return True
    if jti in _token_blacklist:
        return True
    try:
        return bool(await redis_client.exists(f"auth:revoked:{jti}"))
    except Exception:
        return False


async def revoke_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        jti = payload.get("jti")
        if jti:
            _token_blacklist.add(jti)
            expires_in = max(1, int(payload["exp"] - datetime.now(timezone.utc).timestamp()))
            try:
                await redis_client.setex(f"auth:revoked:{jti}", expires_in, "1")
            except Exception:
                logger.warning("Redis unavailable; token revocation is process-local")
    except JWTError:
        pass


def revoke_all_user_tokens(user_id: int):
    pass


def generate_totp_secret() -> str:
    import base64
    import os
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
    if await is_token_revoked(payload):
        raise HTTPException(401, "Token revoked")
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


async def get_user_from_token(token: str, db: AsyncSession):
    from app.models.user import User
    payload = decode_token(token)
    if await is_token_revoked(payload):
        raise HTTPException(401, "Token revoked")
    if payload.get("type") != "access":
        raise HTTPException(401, "Invalid token type")
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(401, "Invalid token")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")
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
        request_id = request.headers.get("x-request-id") or secrets.token_hex(12)
        started_at = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(duration_ms)
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            user_id = None
            authorization = request.headers.get("authorization", "")
            if authorization.startswith("Bearer "):
                try:
                    payload = jwt.decode(
                        authorization[7:], settings.SECRET_KEY,
                        algorithms=[settings.ALGORITHM],
                    )
                    user_id = int(payload["sub"])
                except (JWTError, KeyError, TypeError, ValueError):
                    pass
            audit_details = {
                "audit": True,
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", ""),
                "user_id": user_id,
            }
            logger.info(json.dumps(audit_details))
            if settings.ENVIRONMENT.lower() == "production":
                try:
                    from app.core.database import async_session_factory
                    from app.models.admin import AuditLog
                    async with async_session_factory() as session:
                        session.add(AuditLog(
                            user_id=user_id,
                            action=request.method,
                            resource=request.url.path[:100],
                            details={
                                "request_id": request_id,
                                "status": response.status_code,
                                "duration_ms": duration_ms,
                            },
                            ip_address=audit_details["ip"],
                            user_agent=audit_details["user_agent"][:500],
                        ))
                        await session.commit()
                except Exception as exc:
                    logger.error("Failed to persist audit event: %s", exc)
        return response
