from typing import TYPE_CHECKING, Optional, List
from sqlalchemy import String, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import BaseModel

if TYPE_CHECKING:
    from app.modules.expenses.models import Expense


class Category(BaseModel):
    __tablename__ = "categories"
    __table_args__ = (
        # Composite unique index prevents duplicate categories and speeds up lookups
        Index('idx_categories_name_parent', 'name', 'parent_id', unique=True),
    )

    name: Mapped[str] = mapped_column(String, nullable=False, index=True)

    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Self-referential relationship for subcategories
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), nullable=True, index=True
    )

    # Relationships
    parent: Mapped[Optional["Category"]] = relationship(
        "Category", back_populates="subcategories", remote_side="Category.id"
    )
    
    subcategories: Mapped[List["Category"]] = relationship(
        "Category", back_populates="parent", cascade="all, delete-orphan"
    )

    # Changed from lazy="selectin" to lazy="noload"
    # Prevents loading ALL expenses when fetching a category
    expenses: Mapped[List["Expense"]] = relationship(
        "Expense", back_populates="category", lazy="noload"
    )

    @property
    def full_name(self) -> str:
        """Returns the full category name including parent (e.g., 'Food > Restaurant')"""
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    @property
    def is_subcategory(self) -> bool:
        """Returns True if this is a subcategory (has a parent)"""
        return self.parent_id is not None

    def __repr__(self) -> str:
        return f"<Category(name='{self.full_name}')>"
