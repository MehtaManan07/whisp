"""
Smart Category Classification System
LLM-first approach with exact merchant matching for known vendors.

Architecture:
- Track 1: Known vendor → exact match lookup (fast, 100% accurate for known merchants)
- Track 2: Unknown vendor or description-only → LLM classification (semantic understanding)
"""

import hashlib
import logging
from typing import Optional, Literal
from typing_extensions import TypedDict
import json

from app.core.cache.service import CacheService
from app.integrations.llm.service import LLMService
from .constants import CATEGORIES, KNOWN_MERCHANTS, is_valid_category
from .prompts import build_classification_prompt
from app.intelligence.intent.types import DTO_UNION

logger = logging.getLogger(__name__)


# Type definitions for classification results
ClassificationMethod = Literal["known_merchant", "cache", "llm", "user_pattern", "default"]
ConfidenceLevel = float  # 0.0 to 1.0

# Confidence threshold below which we should ask user to confirm
LOW_CONFIDENCE_THRESHOLD = 0.6


class ClassificationResult(TypedDict):
    """Type-safe classification result structure."""
    category: Optional[str]
    subcategory: Optional[str]
    confidence: ConfidenceLevel
    method: ClassificationMethod
    reasoning: Optional[str]


class CacheableClassification(TypedDict):
    """Type-safe structure for cached classification data."""
    category: Optional[str]
    subcategory: Optional[str]
    confidence: ConfidenceLevel


class CategoryClassifier:
    """
    Two-Track Classification Strategy:
    
    Track 1 - Known Vendors (instant, 100% accurate):
        If we recognize the vendor name exactly, use predefined mapping.
        Examples: "starbucks" → Food & Dining > Cafe/Coffee
        
    Track 2 - LLM Classification (semantic understanding):
        For everything else, use LLM which understands context.
        Examples: "business expense" → Business > Professional Services
                  "training course" → Education > Courses
                  
    The old regex approach is REMOVED because it caused issues like:
        - "business" matching "bus" → wrong Transit category
        - "training" matching "train" → wrong Transit category
        - "dispatch" matching "spa" → wrong Personal Care category
    """

    def __init__(self, cache_service: CacheService, llm_service: LLMService):
        """Initialize CategoryClassifier."""
        self.cache = cache_service
        self.llm = llm_service

    async def classify(
        self,
        original_message: str,
        dto_instance: DTO_UNION,
        user_id: int,
    ) -> ClassificationResult:
        """
        Classify expense using two-track strategy.
        
        Track 1: Known vendor → exact match
        Track 2: Everything else → LLM with full context
        """
        # Extract fields from DTO
        vendor = getattr(dto_instance, "vendor", None)
        note = getattr(dto_instance, "note", None)
        amount = getattr(dto_instance, "amount", None)

        # === TRACK 1: Known vendor exact match ===
        if vendor:
            if result := self._classify_known_vendor(vendor):
                logger.info(f"Known vendor match: {vendor} → {result['category']} > {result['subcategory']}")
                return result
            
            # Check user's historical pattern for this vendor
            if user_id:
                if result := await self._classify_by_user_pattern(user_id, vendor):
                    logger.info(f"User pattern match: {vendor} → {result['category']} > {result['subcategory']}")
                    return result
            
            # Check global cache for this vendor
            cache_key = self._get_cache_key(vendor)
            if cached := await self._get_from_cache(cache_key):
                logger.info(f"Cache hit: {vendor} → {cached['category']} > {cached['subcategory']}")
                return ClassificationResult(
                    category=cached["category"],
                    subcategory=cached["subcategory"],
                    confidence=cached["confidence"],
                    method="cache",
                    reasoning=f"Previously classified vendor: {vendor}",
                )

        # === TRACK 2: LLM classification with full context ===
        result = await self._classify_with_llm(
            original_message=original_message,
            vendor=vendor,
            note=note,
            amount=amount,
        )
        
        # Cache the result if we have a vendor (for future lookups)
        if vendor:
            cache_key = self._get_cache_key(vendor)
            await self._save_to_cache(cache_key, {
                "category": result["category"],
                "subcategory": result["subcategory"],
                "confidence": result["confidence"],
            })
        
        return result

    def _classify_known_vendor(self, vendor: str) -> Optional[ClassificationResult]:
        """
        Exact match against known vendors.
        No regex, no partial matching - just exact lookup.
        """
        normalized_vendor = vendor.lower().strip()
        
        if normalized_vendor in KNOWN_MERCHANTS:
            category, subcategory = KNOWN_MERCHANTS[normalized_vendor]
            return ClassificationResult(
                category=category,
                subcategory=subcategory,
                confidence=0.99,  # Very high confidence for known merchants
                method="known_merchant",
                reasoning=f"Known merchant: {vendor}",
            )
        
        return None

    async def _classify_by_user_pattern(
        self, user_id: int, vendor: str
    ) -> Optional[ClassificationResult]:
        """
        Check user's historical classification for this vendor.
        If the user has corrected this vendor before, use their preference.
        """
        cache_key = f"user_merchant:{user_id}:{vendor.lower().strip()}"
        
        if cached := await self._get_from_cache(cache_key):
            return ClassificationResult(
                category=cached["category"],
                subcategory=cached["subcategory"],
                confidence=cached["confidence"],
                method="user_pattern",
                reasoning=f"User's preferred category for {vendor}",
            )
        
        return None

    async def _classify_with_llm(
        self,
        original_message: str,
        vendor: Optional[str],
        note: Optional[str],
        amount: Optional[float],
    ) -> ClassificationResult:
        """
        Use LLM for semantic classification.
        This is the "brain" that understands context and meaning.
        """
        prompt = build_classification_prompt(
            original_message=original_message,
            vendor=vendor,
            note=note,
            amount=amount,
        )

        try:
            response = await self.llm.complete(
                prompt=prompt,
                temperature=0,  # Deterministic for consistency
                call_stack="categorization",
            )

            result = json.loads(response.content)
            
            # Handle query messages (category and subcategory are null)
            if result.get("category") is None and result.get("subcategory") is None:
                return ClassificationResult(
                    category=None,
                    subcategory=None,
                    confidence=result.get("confidence", 1.0),
                    method="llm",
                    reasoning=result.get("reasoning", "Query, not a transaction"),
                )

            # Validate category/subcategory combination
            category = result.get("category", "Other")
            subcategory = result.get("subcategory", "Miscellaneous")
            
            if not is_valid_category(category, subcategory):
                logger.warning(f"Invalid category combo from LLM: {category} > {subcategory}")
                # Try to fix by finding correct parent category
                if category in CATEGORIES:
                    # Category exists but subcategory doesn't - use first subcategory
                    subcategory = CATEGORIES[category][0]
                else:
                    # Unknown category - fallback to Other
                    category = "Other"
                    subcategory = "Miscellaneous"
                result["confidence"] = min(result.get("confidence", 0.7), 0.7)

            return ClassificationResult(
                category=category,
                subcategory=subcategory,
                confidence=result.get("confidence", 0.8),
                method="llm",
                reasoning=result.get("reasoning"),
            )

        except json.JSONDecodeError as e:
            logger.error(f"LLM returned invalid JSON: {e}")
            return self._get_default_classification("Failed to parse LLM response")
        except Exception as e:
            logger.error(f"LLM classification error: {e}")
            return self._get_default_classification(f"LLM error: {str(e)}")

    def _get_default_classification(self, reason: str) -> ClassificationResult:
        """Return a safe default classification when things go wrong."""
        return ClassificationResult(
            category="Other",
            subcategory="Miscellaneous",
            confidence=0.3,
            method="default",
            reasoning=reason,
        )

    def _get_cache_key(self, vendor: Optional[str]) -> Optional[str]:
        """Generate cache key for vendor."""
        if not vendor:
            return None
        # Use hash to handle long vendor names
        vendor_hash = hashlib.md5(vendor.lower().strip().encode()).hexdigest()
        return f"vendor_cat:{vendor_hash}"

    async def _get_from_cache(self, key: Optional[str]) -> Optional[CacheableClassification]:
        """Retrieve classification from cache."""
        if not key:
            return None

        try:
            cached = await self.cache.get_key(key)
            if cached:
                return cached
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")

        return None

    async def _save_to_cache(
        self, key: Optional[str], data: CacheableClassification, ttl: int = 86400 * 90
    ) -> None:
        """Save classification to cache (90 days default)."""
        if not key:
            return

        try:
            await self.cache.set_key(key, data, ttl)
        except Exception as e:
            logger.warning(f"Cache save error: {e}")

    async def learn_from_correction(
        self,
        user_id: int,
        vendor: Optional[str],
        note: Optional[str],
        old_category: str,
        old_subcategory: str,
        new_category: str,
        new_subcategory: str,
    ) -> None:
        """
        Update patterns when user corrects a category.
        This is how the system learns and improves over time.
        """
        correction_data: CacheableClassification = {
            "category": new_category,
            "subcategory": new_subcategory,
            "confidence": 0.99,  # User corrections are highly trusted
        }

        # If we have a vendor, save user-specific pattern
        if vendor:
            user_cache_key = f"user_merchant:{user_id}:{vendor.lower().strip()}"
            await self._save_to_cache(
                user_cache_key,
                correction_data,
                ttl=86400 * 180,  # 180 days for user preferences
            )
            
            # Also update global vendor cache (lower confidence)
            global_cache_key = self._get_cache_key(vendor)
            if global_cache_key:
                global_correction: CacheableClassification = {
                    "category": new_category,
                    "subcategory": new_subcategory,
                    "confidence": 0.85,
                }
                await self._save_to_cache(
                    global_cache_key,
                    global_correction,
                    ttl=86400 * 30,  # 30 days for global patterns
                )

        # If we have a note/description, save a pattern for it too
        if note:
            note_cache_key = f"user_note:{user_id}:{hashlib.md5(note.lower().strip().encode()).hexdigest()}"
            await self._save_to_cache(
                note_cache_key,
                correction_data,
                ttl=86400 * 90,
            )

        logger.info(
            f"Learned correction: {old_category}>{old_subcategory} → {new_category}>{new_subcategory} "
            f"(vendor={vendor}, note={note})"
        )

    def is_low_confidence(self, result: ClassificationResult) -> bool:
        """Check if the classification result has low confidence and needs user confirmation."""
        return result["confidence"] < LOW_CONFIDENCE_THRESHOLD
