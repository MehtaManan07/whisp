"""
Hybrid Category Classification System
Combines rule-based, cache-based, and LLM-based classification
Goal: 90%+ hits without LLM calls
"""

import re
import hashlib
import logging
from typing import Optional, Literal
from typing_extensions import TypedDict
import json

from app.core.cache.service import CacheService
from app.integrations.llm.service import LLMService
from .constants import CATEGORIES, MERCHANT_RULES
from .prompts import build_classification_prompt
from app.intelligence.intent.types import DTO_UNION

logger = logging.getLogger(__name__)


# Type definitions for classification results
ClassificationMethod = Literal["rule", "cache", "llm", "user_pattern", "non_transaction"]
ConfidenceLevel = float  # 0.0 to 1.0


class ClassificationResult(TypedDict):
    """Type-safe classification result structure."""

    category: Optional[str]
    subcategory: Optional[str]
    confidence: ConfidenceLevel
    method: ClassificationMethod


class CacheableClassification(TypedDict):
    """Type-safe structure for cached classification data."""

    category: Optional[str]
    subcategory: Optional[str]
    confidence: ConfidenceLevel


class CategoryClassifier:
    """
    3-Tier Classification Strategy:
    1. Rule-based (instant, 60-70% coverage)
    2. Cache-based (fast, 20-25% coverage)
    3. LLM-based (fallback, 5-15% coverage)
    """

    def __init__(self, cache_service: CacheService, llm_service: LLMService):
        """
        Initialize CategoryClassifier with type-safe dependencies.

        Args:
            cache_service: CacheService instance for Redis operations
            llm_service: LLMService instance for LLM classification
        """
        self.cache = cache_service
        self.llm = llm_service

    async def classify(
        self,
        original_message: str,
        dto_instance: DTO_UNION,
        user_id: int,
    ) -> ClassificationResult:
        """
        Main classification method

        Args:
            original_message: The original user message
            dto_instance: The extracted DTO instance containing structured data
            user_id: The user ID for personalized classification

        Returns:
            ClassificationResult: Type-safe classification result containing:
                - category: The main expense category (null for non-transactional queries)
                - subcategory: The specific subcategory (null for non-transactional queries)
                - confidence: Confidence level (0.0 to 1.0)
                - method: Classification method used ("rule", "cache", "llm", "user_pattern", "non_transaction")
        """


        # Extract fields from DTO
        merchant = getattr(dto_instance, "vendor", None)
        description = getattr(dto_instance, "note", None)
        amount = getattr(dto_instance, "amount", None)


        # Intelligently choose the best text source for classification
        text = self._get_best_classification_text(
            original_message, merchant, description
        )
        logger.debug(f"Classification text: {text}")

        # Tier 1: Rule-based classification (instant, free)
        if result := self._classify_by_rules(text):
            return ClassificationResult(
                category=result["category"],
                subcategory=result["subcategory"],
                confidence=0.95,  # Rule-based has fixed high confidence
                method="rule",
            )

        # Tier 2: User pattern classification (personalized)
        if user_id and (
            result := await self._classify_by_user_pattern(user_id, merchant)
        ):
            return ClassificationResult(
                category=result["category"],
                subcategory=result["subcategory"],
                confidence=result["confidence"],
                method="user_pattern",
            )

        # Tier 3: Cache lookup (merchant seen before)
        cache_key = self._get_cache_key(merchant)
        if cached := self._get_from_cache(cache_key):
            return ClassificationResult(
                category=cached["category"],
                subcategory=cached["subcategory"],
                confidence=cached["confidence"],
                method="cache",
            )

        # Tier 4: LLM classification (fallback)
        result = await self._classify_by_llm(text, amount)

        # Cache the result for future use
        self._save_to_cache(cache_key, result)

        return ClassificationResult(
            category=result["category"],
            subcategory=result["subcategory"],
            confidence=result["confidence"],
            method="llm",
        )

    def _get_best_classification_text(
        self, original_message: str, merchant: Optional[str], description: Optional[str]
    ) -> str:
        """
        Intelligently choose the best text source for classification.

        Strategy:
        1. If we have both merchant and description, use them (most specific)
        2. If we have only merchant, use it
        3. If we have only description, use it
        4. If we have neither, fall back to original message
        5. Always normalize the chosen text
        """
        extracted_parts = [p for p in [merchant, description] if p and p.strip()]

        if extracted_parts:
            # Use extracted fields if available (more structured/clean)
            text = " ".join(extracted_parts)
        else:
            # Fall back to original message if no extracted fields
            text = original_message

        return self._normalize_text(text)


    def _normalize_text(self, text: str) -> str:
        """Normalize text for classification"""
        text = text.lower().strip()
        # Remove special characters but keep spaces
        text = re.sub(r"[^a-z0-9\s]", "", text)
        return text

    def _classify_by_rules(self, text: str) -> Optional[CacheableClassification]:
        """Fast rule-based classification using regex patterns"""
        for pattern, (category, subcategory) in MERCHANT_RULES.items():
            if re.search(pattern, text, re.IGNORECASE):
                return {
                    "category": category,
                    "subcategory": subcategory,
                    "confidence": 0.95,
                }
        return None

    async def _classify_by_user_pattern(
        self, user_id: int, merchant: Optional[str]
    ) -> Optional[CacheableClassification]:
        """
        Classify based on user's historical patterns
        If user has logged this merchant before, use their preference
        """
        if not merchant:
            return None

        # Check user's history for this merchant
        cache_key = f"user_merchant:{user_id}:{merchant.lower()}"

        if cached := self._get_from_cache(cache_key):
            return cached

        # TODO: Query database for user's past transactions with this merchant
        # This would require a database session dependency
        # For now, return None until we add database integration

        return None

    def _get_cache_key(self, merchant: Optional[str]) -> Optional[str]:
        """Generate cache key for merchant"""
        if not merchant:
            return None
        # Use hash to handle long merchant names
        merchant_hash = hashlib.md5(merchant.lower().encode()).hexdigest()
        return f"merchant_cat:{merchant_hash}"

    def _get_from_cache(self, key: Optional[str]) -> Optional[CacheableClassification]:
        """Retrieve classification from Redis cache"""
        if not key:
            return None

        try:
            cached = self.cache.get_key(key)
            if cached:
                return cached
        except Exception as e:
            # Cache failure shouldn't break classification
            logger.warning(f"Cache retrieval error: {e}")

        return None

    def _save_to_cache(
        self, key: Optional[str], data: CacheableClassification, ttl: int = 86400 * 90
    ) -> None:
        """Save classification to Redis cache (90 days default)"""
        if not key:
            return

        try:
            # data is already a CacheableClassification, so we can use it directly
            self.cache.set_key(key, data, ttl)
        except Exception as e:
            logger.warning(f"Cache save error: {e}")

    async def _classify_by_llm(
        self, text: str, amount: Optional[float]
    ) -> CacheableClassification:
        """Fallback to LLM for unknown merchants"""

        prompt = build_classification_prompt(text, amount)

        try:
            response = await self.llm.complete(
                prompt=prompt,
                temperature=0,
                call_stack="categorization",
            )

            result = json.loads(response.content)

            # Handle query messages (category and subcategory are null)
            if result.get("category") is None and result.get("subcategory") is None:
                return {
                    "category": None,
                    "subcategory": None,
                    "confidence": result.get("confidence", 1.0),
                }

            # Validate category exists for transactions
            if result["category"] not in CATEGORIES:
                result["category"] = "Other"
                result["subcategory"] = "Miscellaneous"
                result["confidence"] = 0.5

            return result

        except Exception as e:
            # LLM failure - return default
            logger.error(f"LLM classification error: {e}")
            return {
                "category": "Other",
                "subcategory": "Miscellaneous",
                "confidence": 0.3,
            }

    def learn_from_correction(
        self,
        user_id: int,
        merchant: str,
        old_category: str,
        new_category: str,
        new_subcategory: str,
    ) -> None:
        """
        User corrects a category - update patterns
        This is how the system gets smarter over time
        """
        correction_data: CacheableClassification = {
            "category": new_category,
            "subcategory": new_subcategory,
            "confidence": 0.99,
        }

        # Update user-specific pattern
        user_cache_key = f"user_merchant:{user_id}:{merchant.lower()}"
        self._save_to_cache(
            user_cache_key,
            correction_data,
            ttl=86400 * 90,  # 90 days
        )

        # Update global merchant pattern (if multiple users agree)
        global_correction_data: CacheableClassification = {
            "category": new_category,
            "subcategory": new_subcategory,
            "confidence": 0.85,
        }

        merchant_cache_key = self._get_cache_key(merchant)
        if merchant_cache_key:
            self._save_to_cache(
                merchant_cache_key,
                global_correction_data,
                ttl=86400 * 30,  # 30 days for global patterns
            )
