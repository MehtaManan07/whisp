from typing import TYPE_CHECKING, Optional, List
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.db.base import BaseModel

if TYPE_CHECKING:
    from app.modules.expenses.models import Expense


class Category(BaseModel):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)

    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationships
    expenses: Mapped[List["Expense"]] = relationship(
        "Expense", back_populates="category", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Category(name='{self.name}')>"
