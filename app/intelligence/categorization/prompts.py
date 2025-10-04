"""
Prompts for category classification
"""

from typing import Optional
from .constants import CATEGORIES


def build_classification_prompt(text: str, amount: Optional[float] = None) -> str:
    """
    Build a prompt for LLM-based category classification.
    
    Args:
        text: The transaction text to classify
        amount: Optional transaction amount
        
    Returns:
        Formatted prompt string for LLM classification
    """
    categories_list = "\n".join(
        [f"- {cat}: {', '.join(subcats)}" for cat, subcats in CATEGORIES.items()]
    )

    prompt = f"""Classify this transaction into category and subcategory.

Transaction: {text}
{f"Amount: ${amount}" if amount else ""}

Available categories:
{categories_list}

Return ONLY valid JSON:
{{
  "category": "exact match from list above",
  "subcategory": "exact match from list above",
  "confidence": 0.0-1.0
}}"""

    return prompt
