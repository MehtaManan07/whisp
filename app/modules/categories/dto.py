from typing import Optional

from pydantic import BaseModel, Field


class CreateCategoryDto(BaseModel):
    name: str = Field(..., description="Name of the category")
    description: Optional[str] = Field(None, description="Description or details about the category")
    parent_id: Optional[int] = Field(None, description="Parent category ID if this is a subcategory")


class CategoryResponseDto(BaseModel):
    id: int = Field(..., description="Unique identifier for the category")
    name: str = Field(..., description="Name of the category")
    description: Optional[str] = Field(None, description="Description or details about the category")
    parent_id: Optional[int] = Field(None, description="Parent category ID if this is a subcategory")
    full_name: str = Field(..., description="Full hierarchical name including parent categories")
    is_subcategory: bool = Field(..., description="Whether this is a subcategory")

    class Config:
        from_attributes = True


class CategoryTreeDto(BaseModel):
    """DTO for category with its subcategories"""
    id: int = Field(..., description="Unique identifier for the category")
    name: str = Field(..., description="Name of the category")
    description: Optional[str] = Field(None, description="Description or details about the category")
    subcategories: list["CategoryTreeDto"] = Field(default_factory=list, description="List of subcategories")

    class Config:
        from_attributes = True
