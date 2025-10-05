"""
Intent Classification System
Simple rule-based classification with LLM fallback
"""

import re
import json
import logging
from typing import Optional

from app.integrations.llm.service import LLMService

from .types import IntentType
from .prompts import INTENT_PATTERNS, build_intent_prompt

logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    Simple 2-Tier Intent Classification:
    1. Rule-based (instant, covers common patterns)
    2. LLM-based (fallback for complex messages)
    """

    def __init__(self, llm_service: LLMService):
        """Initialize the IntentClassifier."""
        self.llm = llm_service

    async def classify(
        self,
        message: str,
    ) -> IntentType:
        """
        Main classification method.

        Args:
            message: User message to classify

        Returns:
            IntentType
        """
        # Normalize the message for processing
        normalized_message = self._normalize_message(message)
        classified_by_rules = self._classify_by_rules(normalized_message)

        # Tier 1: Rule-based classification (instant, covers common patterns)
        if intent := classified_by_rules:
            return intent

        classified_by_llm = await self._classify_by_llm(message)

        # Tier 2: LLM classification (fallback)
        return classified_by_llm

    def _normalize_message(self, message: str) -> str:
        """Normalize message for consistent processing."""
        # Convert to lowercase and strip whitespace
        normalized = message.lower().strip()
        # Remove extra whitespace
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized

    def _classify_by_rules(self, message: str) -> Optional[IntentType]:
        """Fast rule-based classification using regex patterns."""
        for pattern, intent_name in INTENT_PATTERNS.items():
            # Print debug info in different colors for clarity
            if re.search(pattern, message, re.IGNORECASE):
                try:
                    return IntentType(intent_name.lower())
                except ValueError:
                    logger.warning(f"Invalid intent in patterns: {intent_name}")
                    continue
        return None

    async def _classify_by_llm(self, message: str) -> IntentType:
        """Fallback to LLM for complex intent classification."""
        try:
            # Build the prompt
            prompt = build_intent_prompt(message)

            # Make LLM request
            response = await self.llm.complete(
                prompt=prompt,
                temperature=0.1,
                call_stack="intent_classification",
            )

            # Parse the JSON response
            result = json.loads(response.content.strip())

            # Validate and extract intent
            if "intent" in result:
                intent_str = result["intent"].lower()
                try:
                    intent = IntentType(intent_str)
                    return intent
                except ValueError:
                    logger.warning(f"LLM returned invalid intent: {intent_str}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
        except Exception as e:
            logger.error(f"LLM classification error: {e}")

        # Fallback to UNKNOWN if LLM fails
        return IntentType.UNKNOWN
