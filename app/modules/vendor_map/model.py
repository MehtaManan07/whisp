from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import BaseModel, Category


class VendorMap(BaseModel):
    __tablename__ = "vendor_map"

    vendor_name: Mapped[str] = mapped_column(
        String, nullable=False, unique=True, index=True
    )

    # Link directly to category/subcategory
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationships
    category: Mapped["Category"] = relationship("Category", lazy="selectin")

    def __repr__(self) -> str:
        return (
            f"<VendorMap(vendor='{self.vendor_name}', category_id={self.category_id})>"
        )
