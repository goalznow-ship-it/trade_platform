from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.security import hash_password
from app.models.user import User

DEFAULT_ADMIN_EMAIL = "goalznow@gmail.com"
DEFAULT_ADMIN_USERNAME = "goalznow"
DEFAULT_ADMIN_PASSWORD = "abdulabdul"


async def ensure_default_admin(db: AsyncSession) -> bool:
    """Create the default administrator once, identified by email."""
    result = await db.execute(select(User).where(User.email == DEFAULT_ADMIN_EMAIL))
    if result.scalar_one_or_none() is not None:
        return False

    db.add(
        User(
            username=DEFAULT_ADMIN_USERNAME,
            email=DEFAULT_ADMIN_EMAIL,
            hashed_password=hash_password(DEFAULT_ADMIN_PASSWORD),
            is_admin=True,
            is_active=True,
            subscription_tier="elite",
        )
    )
    await db.commit()
    logger.info("Default administrator created")
    return True
