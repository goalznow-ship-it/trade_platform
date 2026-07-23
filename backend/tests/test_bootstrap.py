from sqlalchemy import func, select

from app.core.bootstrap import (
    DEFAULT_ADMIN_EMAIL,
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_USERNAME,
    ensure_default_admin,
)
from app.core.security import verify_password
from app.models.user import User


async def test_ensure_default_admin_creates_expected_account(db_session):
    created = await ensure_default_admin(db_session)

    result = await db_session.execute(
        select(User).where(User.email == DEFAULT_ADMIN_EMAIL)
    )
    user = result.scalar_one()

    assert created is True
    assert user.username == DEFAULT_ADMIN_USERNAME
    assert verify_password(DEFAULT_ADMIN_PASSWORD, user.hashed_password)
    assert user.is_admin is True
    assert user.is_active is True
    assert user.subscription_tier == "elite"


async def test_ensure_default_admin_does_not_create_duplicate(db_session):
    assert await ensure_default_admin(db_session) is True
    assert await ensure_default_admin(db_session) is False

    count = await db_session.scalar(
        select(func.count(User.id)).where(User.email == DEFAULT_ADMIN_EMAIL)
    )
    assert count == 1
