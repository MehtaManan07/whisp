from typing import List
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from app.infra.db.engine import get_db
from app.infra.middleware.request_id_middleware import RequestIDMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db import User

app = FastAPI(
    title="Whisp API",
    description="A messaging and user management API",
    version="1.0.0",
)

# Middlewares
app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_all_users(db: AsyncSession) -> List[User]:
    """Fetch all users from database"""
    result = await db.execute(select(User))
    users = result.scalars().all()
    return list(users)


@app.get("/users", response_model=List[dict])
async def list_users(db: AsyncSession = Depends(get_db)):
    """Get all users"""
    users = await get_all_users(db)
    return [{"id": user.id, "wa_id": user.wa_id, "name": user.name} for user in users]


@app.get("/demo")
async def demo(request: Request) -> dict[str, str]:
    return {"message": "Hello World", "request_id": str(request.state.request_id)}
