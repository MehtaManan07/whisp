from typing import Optional

from pydantic import BaseModel


class CreateCategoryDto(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None


class CategoryResponseDto(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    full_name: str
    is_subcategory: bool

    class Config:
        from_attributes = True


class CategoryTreeDto(BaseModel):
    """DTO for category with its subcategories"""
    id: int
    name: str
    description: Optional[str] = None
    subcategories: list["CategoryTreeDto"] = []

    class Config:
        from_attributes = True
