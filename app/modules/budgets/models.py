from typing import TYPE_CHECKING, Optional
from sqlalchemy import ForeignKey, String, Float, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import BaseModel

if TYPE_CHECKING:
    from app.modules.users.models import User


class Budget(BaseModel):
    __tablename__ = "budgets"
    __table_args__ = (
        Index("idx_budgets_user_active", "user_id", "is_active"),
        Index("idx_budgets_lookup", "user_id", "category_name", "period"),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    category_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="Parent-level category name (e.g., 'Food & Dining')",
    )

    amount_limit: Mapped[float] = mapped_column(Float, nullable=False)

    period: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="'weekly' or 'monthly'",
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship("User", lazy="noload")

    def __repr__(self) -> str:
        return f"<Budget(user_id={self.user_id}, category='{self.category_name}', limit={self.amount_limit}, period='{self.period}')>"
