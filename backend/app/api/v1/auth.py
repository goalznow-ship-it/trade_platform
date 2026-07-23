from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, or_, select
from pydantic import BaseModel, Field
from app.core.database import get_db
from app.core.security import (
    create_access_token, create_refresh_token, decode_token, get_current_user,
    hash_password, is_token_revoked, revoke_token, verify_password,
)
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    email: str
    password: str = Field(min_length=10, max_length=128)

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict

class RefreshRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None

@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(User).where((User.username == req.username) | (User.email == req.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Username or email already exists")
    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"message": "User created", "user_id": user.id}

@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    identifier = req.username.strip().lower()
    result = await db.execute(
        select(User).where(
            or_(
                func.lower(User.username) == identifier,
                func.lower(User.email) == identifier,
            )
        )
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(401, "Account disabled")

    from datetime import datetime, timezone
    user.last_login = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()

    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id), "admin": user.is_admin}),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "display_name": user.display_name,
        }
    )

@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
        "display_name": user.display_name,
        "timezone": user.timezone,
        "language": user.language,
        "theme": user.theme,
        "balance": user.balance,
        "total_pnl": user.total_pnl,
        "win_rate": user.win_rate,
        "subscription_tier": user.subscription_tier,
        "created_at": str(user.created_at),
    }

@router.post("/refresh")
async def refresh_token(
    req: RefreshRequest | None = Body(default=None),
    token: str | None = Query(default=None, deprecated=True),
    db: AsyncSession = Depends(get_db),
):
    supplied_token = req.refresh_token if req else token
    if not supplied_token:
        raise HTTPException(422, "refresh_token is required")
    payload = decode_token(supplied_token)
    if payload.get("type") != "refresh" or await is_token_revoked(payload):
        raise HTTPException(401, "Invalid token type")
    result = await db.execute(select(User).where(User.id == int(payload["sub"])))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")
    await revoke_token(supplied_token)
    return {
        "access_token": create_access_token({"sub": str(user.id), "admin": user.is_admin}),
        "refresh_token": create_refresh_token({"sub": str(user.id)}),
        "token_type": "bearer",
    }

@router.post("/logout", status_code=204)
async def logout(
    req: LogoutRequest,
    user: User = Depends(get_current_user),
):
    if req.access_token:
        await revoke_token(req.access_token)
    if req.refresh_token:
        payload = decode_token(req.refresh_token)
        if payload.get("sub") != str(user.id):
            raise HTTPException(403, "Token does not belong to current user")
        await revoke_token(req.refresh_token)
