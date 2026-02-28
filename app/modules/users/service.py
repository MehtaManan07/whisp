import logging
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from typing import Optional, List

from app.modules.users.models import User
from app.modules.users.dto import CreateUserDto, UpdateUserDto, UserResponseDto
from app.modules.users.types import FindOrCreateResult
from app.utils.timezone_detection import detect_timezone_from_phone
from app.utils.datetime import utc_now
from app.core.db.engine import run_db

logger = logging.getLogger(__name__)


class UsersService:
    def __init__(self):
        self.logger = logger

    # -------------------------------------------------------------------------
    # Sync helpers (called from within run_db blocks in other services)
    # -------------------------------------------------------------------------

    def find_or_create_sync(self, db: Session, user_data: CreateUserDto) -> FindOrCreateResult:
        """Find existing user or create new one (sync)."""
        result = db.execute(select(User).where(User.wa_id == user_data.wa_id))
        user = result.scalar_one_or_none()

        if user:
            return {"user": user, "is_existing_user": True}

        detected_timezone = "UTC"
        if user_data.phone_number:
            detected_timezone = detect_timezone_from_phone(user_data.phone_number)
            self.logger.info(
                f"Detected timezone {detected_timezone} for phone {user_data.phone_number}"
            )

        new_user = User(
            wa_id=user_data.wa_id,
            name=user_data.name,
            phone_number=user_data.phone_number,
            timezone=detected_timezone,
            meta=user_data.meta,
            streak=0,
            created_at=utc_now(),
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {"user": new_user, "is_existing_user": False}

    def get_user_by_id_sync(self, db: Session, user_id: int) -> Optional[User]:
        result = db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    # -------------------------------------------------------------------------
    # Async public API
    # -------------------------------------------------------------------------

    async def find_or_create(self, user_data: CreateUserDto) -> FindOrCreateResult:
        return await run_db(lambda db: self.find_or_create_sync(db, user_data))

    async def get_or_create_by_phone(self, phone_number: str) -> User:
        user_data = CreateUserDto(
            wa_id=phone_number,
            phone_number=phone_number,
            name=None,
            meta=None,
        )
        result = await self.find_or_create(user_data)
        return result["user"]

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        return await run_db(lambda db: self.get_user_by_id_sync(db, user_id))

    async def get_user_by_wa_id(self, wa_id: str) -> Optional[User]:
        def _get(db: Session) -> Optional[User]:
            result = db.execute(select(User).where(User.wa_id == wa_id))
            return result.scalar_one_or_none()

        return await run_db(_get)

    async def get_all_users(
        self, limit: int = 100, offset: int = 0
    ) -> List[User]:
        def _get(db: Session) -> List[User]:
            result = db.execute(
                select(User).offset(offset).limit(limit).order_by(User.created_at.desc())
            )
            return list(result.scalars().all())

        return await run_db(_get)

    async def update_user(
        self, user_id: int, update_data: UpdateUserDto
    ) -> Optional[User]:
        def _update(db: Session) -> Optional[User]:
            update_dict = update_data.model_dump(exclude_unset=True)
            if not update_dict:
                return self.get_user_by_id_sync(db, user_id)

            result = db.execute(
                update(User).where(User.id == user_id).values(**update_dict).returning(User)
            )
            updated_user = result.scalar_one_or_none()

            if updated_user:
                db.commit()

            return updated_user

        return await run_db(_update)

    async def delete_user(self, user_id: int) -> bool:
        def _delete(db: Session) -> bool:
            user = self.get_user_by_id_sync(db, user_id)
            if not user:
                return False

            db.delete(user)
            db.commit()
            return True

        return await run_db(_delete)

    async def update_user_timezone(
        self, user_id: int, timezone: str
    ) -> Optional[User]:
        update_data = UpdateUserDto(
            timezone=timezone, name=None, phone_number=None, meta=None
        )
        return await self.update_user(user_id, update_data)

    def get_user_timezone(self, user: User) -> str:
        """Get user's timezone, with fallback to UTC"""
        return user.timezone if user and user.timezone else "UTC"


# Global service instance
users_service = UsersService()
