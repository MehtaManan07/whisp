import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.db import User
from app.modules.users.dto import CreateUserDto
from app.modules.users.types import FindOrCreateResult

logger = logging.getLogger(__name__)


class UsersService:
    def __init__(self):
        self.logger = logger

    async def find_or_create(
        self, db: AsyncSession, user_data: CreateUserDto
    ) -> FindOrCreateResult:
        """Find existing user or create new one"""
        # Try to find existing user
        result = await db.execute(select(User).where(User.wa_id == user_data.wa_id))
        user = result.scalar_one_or_none()

        if user:
            return {"user": user, "is_existing_user": True}

        # Create new user
        self.logger.info(f"Creating new user with wa_id: {user_data.wa_id}")

        new_user = User(
            wa_id=user_data.wa_id,
            name=user_data.name,
            phone_number=user_data.phone_number,
            meta=user_data.meta,
            streak=0,
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        return {"user": new_user, "is_existing_user": False}


# Global service instance
users_service = UsersService()
