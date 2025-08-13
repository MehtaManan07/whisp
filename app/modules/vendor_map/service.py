import logging
import re
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.db import VendorMap, Category
from app.utils.datetime import utc_now

logger = logging.getLogger(__name__)


class VendorMapService:
    def __init__(self):
        self.logger = logger

    async def get_category_for_vendor(
        self, db: AsyncSession, vendor_name: str
    ) -> Optional[Category]:
        """
        Fetch mapped category for a vendor.
        Returns None if no mapping exists.
        """
        normalized_name = self.normalize_vendor_name(vendor_name)

        query = (
            select(VendorMap)
            .options(selectinload(VendorMap.category))
            .where(VendorMap.vendor_name == normalized_name)
        )

        result = await db.execute(query)
        vendor_map = result.scalar_one_or_none()

        if vendor_map:
            return vendor_map.category

        return None

    async def map_vendor_to_category(
        self, db: AsyncSession, vendor_name: str, category_id: int
    ) -> VendorMap:
        """
        Create mapping between vendor and category.
        Raises ValueError if mapping already exists or category doesn't exist.
        """
        normalized_name = self.normalize_vendor_name(vendor_name)

        # Check if vendor mapping already exists
        existing_query = select(VendorMap).where(
            VendorMap.vendor_name == normalized_name
        )
        existing_result = await db.execute(existing_query)
        existing_mapping = existing_result.scalar_one_or_none()

        if existing_mapping:
            raise ValueError(
                f"Vendor '{vendor_name}' is already mapped to category_id {existing_mapping.category_id}"
            )

        # Verify category exists
        category_query = select(Category).where(Category.id == category_id)
        category_result = await db.execute(category_query)
        category = category_result.scalar_one_or_none()

        if not category:
            raise ValueError(f"Category with id {category_id} does not exist")

        # Create new mapping
        new_mapping = VendorMap(vendor_name=normalized_name, category_id=category_id)

        db.add(new_mapping)
        await db.commit()
        await db.refresh(new_mapping)

        return new_mapping

    async def update_vendor_mapping(
        self, db: AsyncSession, vendor_name: str, category_id: int
    ) -> VendorMap:
        """
        Change existing mapping to a different category.
        Raises ValueError if mapping doesn't exist or new category doesn't exist.
        """
        normalized_name = self.normalize_vendor_name(vendor_name)

        # Find existing mapping
        mapping_query = (
            select(VendorMap)
            .options(selectinload(VendorMap.category))
            .where(VendorMap.vendor_name == normalized_name)
        )
        mapping_result = await db.execute(mapping_query)
        existing_mapping = mapping_result.scalar_one_or_none()

        if not existing_mapping:
            raise ValueError(f"No mapping exists for vendor '{vendor_name}'")

        # Verify new category exists
        category_query = select(Category).where(Category.id == category_id)
        category_result = await db.execute(category_query)
        new_category = category_result.scalar_one_or_none()

        if not new_category:
            raise ValueError(f"Category with id {category_id} does not exist")

        # Update mapping
        old_category_name = existing_mapping.category.full_name
        existing_mapping.category_id = category_id

        await db.commit()
        await db.refresh(existing_mapping)

        return existing_mapping

    async def delete_vendor_mapping(self, db: AsyncSession, vendor_name: str) -> None:
        """
        Remove mapping for a vendor.
        Raises ValueError if mapping doesn't exist.
        """
        normalized_name = self.normalize_vendor_name(vendor_name)

        # Find existing mapping first to verify it exists
        mapping_query = (
            select(VendorMap)
            .options(selectinload(VendorMap.category))
            .where(VendorMap.vendor_name == normalized_name)
        )
        mapping_result = await db.execute(mapping_query)
        existing_mapping = mapping_result.scalar_one_or_none()

        if not existing_mapping:
            raise ValueError(f"No mapping exists for vendor '{vendor_name}'")

        existing_mapping.deleted_at = utc_now()
        await db.commit()
        await db.refresh(existing_mapping)

    async def bulk_map_vendors(
        self, db: AsyncSession, vendor_category_pairs: List[Tuple[str, int]]
    ) -> None:
        """
        Batch insert/update vendor mappings.
        Creates new mappings or updates existing ones.
        Validates all categories exist before processing.
        """
        if not vendor_category_pairs:
            return

        # Normalize vendor names and extract unique category IDs
        normalized_pairs = [
            (self.normalize_vendor_name(vendor), category_id)
            for vendor, category_id in vendor_category_pairs
        ]
        unique_category_ids = list(set(pair[1] for pair in normalized_pairs))

        # Verify all categories exist
        categories_query = select(Category).where(Category.id.in_(unique_category_ids))
        categories_result = await db.execute(categories_query)
        existing_categories = {cat.id for cat in categories_result.scalars().all()}

        missing_categories = set(unique_category_ids) - existing_categories
        if missing_categories:
            raise ValueError(
                f"Categories with IDs {list(missing_categories)} do not exist"
            )

        # Get existing mappings to determine which need updates vs inserts
        vendor_names = [pair[0] for pair in normalized_pairs]
        existing_mappings_query = select(VendorMap).where(
            VendorMap.vendor_name.in_(vendor_names)
        )
        existing_mappings_result = await db.execute(existing_mappings_query)
        existing_mappings = {
            mapping.vendor_name: mapping
            for mapping in existing_mappings_result.scalars().all()
        }

        updates_count = 0
        inserts_count = 0

        # Process each mapping
        for vendor_name, category_id in normalized_pairs:
            if vendor_name in existing_mappings:
                # Update existing mapping
                existing_mapping = existing_mappings[vendor_name]
                if existing_mapping.category_id != category_id:
                    existing_mapping.category_id = category_id
                    updates_count += 1
            else:
                # Create new mapping
                new_mapping = VendorMap(
                    vendor_name=vendor_name, category_id=category_id
                )
                db.add(new_mapping)
                inserts_count += 1

        await db.commit()

    def normalize_vendor_name(self, vendor_name: str) -> str:
        """
        Utility for cleaning vendor names before saving/searching.
        Converts to lowercase, removes extra whitespace and special characters.
        """
        if not vendor_name:
            return ""

        # Convert to lowercase
        normalized = vendor_name.lower()

        # Remove extra whitespace
        normalized = re.sub(r"\s+", " ", normalized).strip()

        # Remove common suffixes/prefixes that might vary
        # e.g., "Inc.", "LLC", "Ltd.", "Corp.", etc.
        suffixes_to_remove = [
            r"\binc\.?$",
            r"\bllc\.?$",
            r"\bltd\.?$",
            r"\bcorp\.?$",
            r"\bco\.?$",
            r"\bcompany$",
            r"\blimited$",
        ]

        for suffix in suffixes_to_remove:
            normalized = re.sub(suffix, "", normalized).strip()

        # Remove common punctuation but keep spaces and alphanumeric
        normalized = re.sub(r"[^\w\s-]", "", normalized)

        # Final cleanup of multiple spaces
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized
