from typing import TYPE_CHECKING, Optional, List
from sqlalchemy import ForeignKey, Float, Boolean, Index, Enum as SQLEnum, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import BaseModel

if TYPE_CHECKING:
    from app.modules.users.models import User
    from app.modules.categories.models import Category


class Budget(BaseModel):
    __tablename__ = "budgets"
    __table_args__ = (
        # Indexes for query performance
        Index("idx_budgets_user_period", "user_id", "period"),
        Index("idx_budgets_category", "category_id"),
        Index("idx_budgets_is_active", "is_active"),
        Index("idx_budgets_deleted_at", "deleted_at"),
    )

    # Foreign key relationships
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )

    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), nullable=True, index=True
    )

    # Budget fields
    period: Mapped[str] = mapped_column(String, nullable=False)

    amount: Mapped[float] = mapped_column(Float, nullable=False)

    alert_thresholds: Mapped[List[float]] = mapped_column(
        JSON, nullable=False, default=[80, 100]
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="budgets", lazy="noload")

    category: Mapped[Optional["Category"]] = relationship(
        "Category", back_populates="budgets", lazy="noload"
    )

    def __repr__(self) -> str:
        category_info = f", category_id={self.category_id}" if self.category_id else ""
        return f"<Budget(user_id={self.user_id}, period={self.period}, amount={self.amount}{category_info})>"
