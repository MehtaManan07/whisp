from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class CreateUserDto(BaseModel):
    telegram_id: str = Field(..., description="Telegram user ID")
    name: Optional[str] = Field(None, description="User's full name")
    phone_number: Optional[str] = Field(None, description="User's phone number")
    meta: Optional[Dict[str, Any]] = Field(None, description="Additional metadata about the user")


class UpdateUserDto(BaseModel):
    name: Optional[str] = Field(None, description="User's full name")
    phone_number: Optional[str] = Field(None, description="User's phone number")
    timezone: Optional[str] = Field(None, description="IANA timezone identifier (e.g., 'Asia/Kolkata')")
    meta: Optional[Dict[str, Any]] = Field(None, description="Additional metadata about the user")


class UserResponseDto(BaseModel):
    id: int = Field(..., description="Unique identifier for the user")
    telegram_id: Optional[str] = Field(None, description="Telegram user ID")
    name: Optional[str] = Field(None, description="User's full name")
    phone_number: Optional[str] = Field(None, description="User's phone number")
    timezone: Optional[str] = Field("UTC", description="IANA timezone identifier")
    last_active: Optional[datetime] = Field(None, description="Last time user was active")
    streak: int = Field(..., description="Current activity streak count")
    meta: Optional[Dict[str, Any]] = Field(None, description="Additional metadata about the user")
    created_at: datetime = Field(..., description="When the user account was created")
    updated_at: Optional[datetime] = Field(None, description="When the user account was last updated")

    class Config:
        from_attributes = True
