from fastapi import APIRouter, Query
from typing import List, Optional

from app.core.dependencies import UserServiceDep
from app.core.exceptions import UserNotFoundError, ValidationError, ConflictError
from app.modules.users.dto import CreateUserDto, UpdateUserDto, UserResponseDto
from app.modules.users.types import FindOrCreateResult

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserResponseDto)
async def create_user(
    user_data: CreateUserDto,
    user_service: UserServiceDep,
) -> UserResponseDto:
    """Create a new user or return existing one"""
    if not user_data.wa_id:
        raise ValidationError("WhatsApp ID is required")

    result: FindOrCreateResult = await user_service.find_or_create(user_data)
    return UserResponseDto.model_validate(result["user"])


@router.get("/{user_id}", response_model=UserResponseDto)
async def get_user(
    user_id: int,
    user_service: UserServiceDep,
) -> UserResponseDto:
    """Get user by ID"""
    if user_id <= 0:
        raise ValidationError("User ID must be a positive integer")

    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise UserNotFoundError(user_id)

    return UserResponseDto.model_validate(user)


@router.get("/wa/{wa_id}", response_model=UserResponseDto)
async def get_user_by_wa_id(
    wa_id: str,
    user_service: UserServiceDep,
) -> UserResponseDto:
    """Get user by WhatsApp ID"""
    if not wa_id or not wa_id.strip():
        raise ValidationError("WhatsApp ID is required")

    user = await user_service.get_user_by_wa_id(wa_id)
    if not user:
        raise UserNotFoundError(wa_id)

    return UserResponseDto.model_validate(user)


@router.get("/", response_model=List[UserResponseDto])
async def get_all_users(
    user_service: UserServiceDep,
    limit: int = Query(default=100, ge=1, le=1000, description="Number of users to return"),
    offset: int = Query(default=0, ge=0, description="Number of users to skip"),
) -> List[UserResponseDto]:
    """Get all users with pagination"""
    if limit <= 0 or limit > 1000:
        raise ValidationError("Limit must be between 1 and 1000")

    if offset < 0:
        raise ValidationError("Offset must be non-negative")

    users = await user_service.get_all_users(limit=limit, offset=offset)
    return [UserResponseDto.model_validate(user) for user in users]


@router.put("/{user_id}", response_model=UserResponseDto)
async def update_user(
    user_id: int,
    update_data: UpdateUserDto,
    user_service: UserServiceDep,
) -> UserResponseDto:
    """Update user by ID"""
    if user_id <= 0:
        raise ValidationError("User ID must be a positive integer")

    updated_user = await user_service.update_user(user_id, update_data)
    if not updated_user:
        raise UserNotFoundError(user_id)

    return UserResponseDto.model_validate(updated_user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    user_service: UserServiceDep,
) -> dict:
    """Delete user by ID"""
    if user_id <= 0:
        raise ValidationError("User ID must be a positive integer")

    success = await user_service.delete_user(user_id)
    if not success:
        raise UserNotFoundError(user_id)

    return {"message": "User deleted successfully"}
