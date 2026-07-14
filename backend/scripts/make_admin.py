"""
Usage: python scripts/make_admin.py <email>

Promotes a user to admin (is_admin=True, subscription_tier="elite").
Safe to run repeatedly — only modifies the target user.
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings
from app.models.user import User


async def promote(email: str) -> bool:
    from app.core.database import Base as AppBase

    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(AppBase.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            print(f"User with email '{email}' not found.")
            return False

        user.is_admin = True
        user.subscription_tier = "elite"
        await session.commit()
        print(f"Promoted '{email}' (id={user.id}) to admin + elite subscription.")
        return True

    await engine.dispose()


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/make_admin.py <email>")
        sys.exit(1)

    email = sys.argv[1].strip()
    success = asyncio.run(promote(email))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
