from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict

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
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(401, "Account disabled")

    user.last_login = __import__('datetime').datetime.utcnow()
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
async def refresh_token(token: str):
    from app.core.security import decode_token
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid token type")
    return {
        "access_token": create_access_token({"sub": payload["sub"]}),
        "token_type": "bearer",
    }
