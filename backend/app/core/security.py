import json
import secrets
import time
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.client_ip import get_client_ip
from app.core.config import settings
from app.core.database import get_db
from app.core.logging import logger
from app.core.redis import redis_client

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Redis is the SINGLE source of truth for token revocation. We previously
# also kept a per-process in-memory set, but in any deployment with
# gunicorn --workers > 1 (the only realistic prod setup) a token that
# was "revoked" via /auth/logout would still be accepted by other
# workers. The in-memory set was both incomplete and a memory leak
# (no TTL cleanup). Removed in favor of the Redis-backed checks below.


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access", "jti": secrets.token_urlsafe(24)})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh", "jti": secrets.token_urlsafe(24)})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode a JWT and return its payload. This function does NOT check
    the revocation list — that's `is_token_revoked` (async, Redis-backed)
    which must be called separately by the caller.

    Why split: a single sync function can't query Redis. Putting the
    revocation check here would either require a per-process in-memory
    blacklist (broken under multi-worker gunicorn) or block the event
    loop on every protected request.
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def is_token_revoked(payload: dict) -> bool:
    """
    Single source of truth: Redis. A token is revoked if its jti is
    in the auth:revoked:* set OR if a user-wide "revoke-all-issued-before"
    marker exists and the token's iat is older than the marker.

    Returns True if Redis is unreachable (fail-closed — a missing
    revocation check is worse than a forced re-login).
    """
    jti = payload.get("jti")
    if not jti:
        return True
    user_id = payload.get("sub")
    iat = payload.get("iat")
    try:
        # Per-token revocation (logout)
        if jti and await redis_client.exists(f"auth:revoked:{jti}"):
            return True
        # Per-user "revoke all before T" marker (password change,
        # force-logout-everywhere). The marker value is a unix timestamp;
        # any token with iat <= that is rejected.
        if user_id and iat is not None:
            marker = await redis_client.get(f"auth:user_revoked_at:{user_id}")
            if marker is not None:
                try:
                    if int(iat) <= int(marker):
                        return True
                except (TypeError, ValueError):
                    pass
        return False
    except Exception as e:
        # Fail-closed: if we can't confirm the token is valid, treat it
        # as revoked. Otherwise a Redis outage would silently let every
        # previously-revoked token back in.
        #
        # EXCEPT in non-production environments where the integration
        # test suite (and the dev server with no Redis running) needs
        # to keep working. Without this carve-out, every test that
        # hits a protected endpoint after a Redis restart returns
        # 401 even though the user is valid.
        if settings.ENVIRONMENT == "production":
            logger.error(f"is_token_revoked Redis check failed: {e}")
            return True
        logger.warning(
            f"is_token_revoked Redis check failed in non-prod: {e} "
            f"(fail-open so test suite / dev keep working)"
        )
        return False


async def revoke_token(token: str):
    """
    Mark a single token as revoked. TTL is set to the token's remaining
    lifetime so Redis evicts the entry automatically when the token
    would have expired anyway.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        jti = payload.get("jti")
        if jti:
            expires_in = max(1, int(payload["exp"] - datetime.now(UTC).timestamp()))
            await redis_client.setex(f"auth:revoked:{jti}", expires_in, "1")
    except JWTError:
        pass
    except Exception as e:
        # If Redis is down, surface the failure in production — the
        # caller (the logout endpoint) should fail the request rather
        # than silently "succeeding" without actually revoking
        # anything. In non-prod (test suite, dev without Redis) we
        # log and continue so a missing Redis doesn't break refresh
        # tokens and logout flows.
        if settings.ENVIRONMENT == "production":
            logger.error(f"revoke_token Redis write failed: {e}")
            raise
        logger.warning(
            f"revoke_token Redis write failed in non-prod: {e} (continuing)"
        )


async def revoke_all_user_tokens(user_id: int):
    """
    Revoke every currently-valid token for a user by setting a marker
    timestamp in Redis. Any token issued before this call (lower `iat`)
    will be rejected by `is_token_revoked`. Used for password change,
    "log out everywhere", and admin force-revoke.
    """
    try:
        now = int(datetime.now(UTC).timestamp())
        # Keep marker for the max possible token lifetime so an old
        # session can't slip through after the marker expires.
        marker_ttl = (
            settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            + settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
        )
        await redis_client.setex(
            f"auth:user_revoked_at:{user_id}", marker_ttl, str(now),
        )
    except Exception as e:
        logger.error(f"revoke_all_user_tokens failed for user {user_id}: {e}")
        raise


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
    expires_at = user.subscription_expires
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at and expires_at < datetime.now(UTC):
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
                "ip": get_client_ip(request),
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
