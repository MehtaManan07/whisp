import asyncio
from typing import TypeVar, Callable

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import config as settings

T = TypeVar("T")

_url = settings.turso_database_url.replace("libsql://", "sqlite+libsql://") + "?secure=true"

engine = create_engine(
    _url,
    connect_args={"auth_token": settings.turso_auth_token},
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600,
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


async def run_db(fn: Callable[[Session], T]) -> T:
    """Run a sync DB function in a thread pool for async compatibility."""
    def _execute():
        with SessionLocal() as session:
            try:
                result = fn(session)
                session.commit()
                return result
            except Exception:
                session.rollback()
                raise

    return await asyncio.to_thread(_execute)
