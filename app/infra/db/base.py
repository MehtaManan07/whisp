# import contextlib
# from typing import Any, AsyncIterator
# from sqlalchemy import NullPool
# from sqlalchemy.ext.asyncio import (
#     AsyncConnection,
#     AsyncSession,
#     async_sessionmaker,
#     create_async_engine,
# )
# from sqlalchemy.orm import declarative_base
# from app.infra.config import config as settings

# Base = declarative_base()


# class DatabaseSessionManager:
#     def __init__(self, host: str, engine_kwargs: dict[str, Any] = {}):
#         self._engine = create_async_engine(host, poolclass=NullPool, **engine_kwargs)
#         self._sessionmaker = async_sessionmaker(
#             autocommit=False, bind=self._engine, expire_on_commit=False
#         )

#     def init(self, host: str):
#         self._engine = create_async_engine(host, poolclass=NullPool)
#         self._sessionmaker = async_sessionmaker(autocommit=False, bind=self._engine)

#     async def close(self):
#         if self._engine is None:
#             raise Exception("DatabaseSessionManager is not initialized")
#         await self._engine.dispose()
#         self._engine = None
#         self._sessionmaker = None

#     @contextlib.asynccontextmanager
#     async def connect(self) -> AsyncIterator[AsyncConnection]:
#         if self._engine is None:
#             raise Exception("DatabaseSessionManager is not initialized")

#         async with self._engine.begin() as connection:
#             try:
#                 yield connection
#             except Exception:
#                 await connection.rollback()
#                 raise

#     @contextlib.asynccontextmanager
#     async def session(self) -> AsyncIterator[AsyncSession]:
#         if self._sessionmaker is None:
#             raise Exception("DatabaseSessionManager is not initialized")

#         session = self._sessionmaker()
#         try:
#             yield session
#         except Exception:
#             await session.rollback()
#             raise
#         finally:
#             await session.close()

#     async def create_all(self, connection: AsyncConnection):
#         await connection.run_sync(Base.metadata.create_all)

#     async def drop_all(self, connection: AsyncConnection):
#         await connection.run_sync(Base.metadata.drop_all)


# sessionmanager = DatabaseSessionManager(settings.db_url, {"echo": True})


from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import Optional
import uuid


class Base(DeclarativeBase):
    """Base class for all database models"""

    pass


class BaseModel(Base):
    """
    Abstract base model that provides common fields for all entities.
    Similar to TypeORM's BaseEntity but with SQLAlchemy 2.0 style.
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
    
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
