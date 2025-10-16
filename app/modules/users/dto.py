from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class CreateUserDto(BaseModel):
    wa_id: str
    name: Optional[str] = None
    phone_number: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class UpdateUserDto(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None
    timezone: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class UserResponseDto(BaseModel):
    id: int
    wa_id: str
    name: Optional[str] = None
    phone_number: Optional[str] = None
    timezone: Optional[str] = "UTC"
    last_active: Optional[datetime] = None
    streak: int
    meta: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # For Pydantic v2 (was orm_mode in v1)
