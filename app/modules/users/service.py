import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Optional, List

from app.core.db import User
from app.modules.users.dto import CreateUserDto, UpdateUserDto, UserResponseDto
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

    async def get_or_create_by_phone(self, db: AsyncSession, phone_number: str) -> User:
        """Get or create user by phone number (for WhatsApp integration)"""
        # This method is used by the orchestrator
        user_data = CreateUserDto(
            wa_id=phone_number,  # Use phone as wa_id for now
            phone_number=phone_number
        )
        result = await self.find_or_create(db, user_data)
        return result["user"]

    async def get_user_by_id(self, db: AsyncSession, user_id: int) -> Optional[User]:
        """Get user by ID"""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_wa_id(self, db: AsyncSession, wa_id: str) -> Optional[User]:
        """Get user by WhatsApp ID"""
        result = await db.execute(select(User).where(User.wa_id == wa_id))
        return result.scalar_one_or_none()

    async def get_all_users(self, db: AsyncSession, limit: int = 100, offset: int = 0) -> List[User]:
        """Get all users with pagination"""
        result = await db.execute(
            select(User).offset(offset).limit(limit).order_by(User.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_user(self, db: AsyncSession, user_id: int, update_data: UpdateUserDto) -> Optional[User]:
        """Update user by ID - Optimized to use 1 query instead of 3"""
        # Update only provided fields
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            # If no updates, just fetch and return
            return await self.get_user_by_id(db, user_id)

        # Fetch and update in same transaction using RETURNING clause
        # This is more efficient than separate fetch-update-fetch
        result = await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(**update_dict)
            .returning(User)
        )
        updated_user = result.scalar_one_or_none()
        
        if updated_user:
            await db.commit()
        
        return updated_user

    async def delete_user(self, db: AsyncSession, user_id: int) -> bool:
        """Delete user by ID"""
        user = await self.get_user_by_id(db, user_id)
        if not user:
            return False

        await db.delete(user)
        await db.commit()
        return True


# Global service instance
users_service = UsersService()
