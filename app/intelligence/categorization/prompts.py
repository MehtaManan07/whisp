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

    prompt = f"""Classify this message into category and subcategory.

Message: {text}
{f"Amount: ${amount}" if amount else ""}

IMPORTANT: First determine if this is a QUERY or a TRANSACTION:

QUERY examples (return null for category/subcategory):
- "show me all expenses of this month"
- "how much did I spend this month"
- "list my expenses"
- "what did I spend on groceries"
- "total spending this month"
- "expenses by category"
- "monthly spending summary"
- "where did I spend my money"
- "breakdown of my expenses"
- "display all transactions"
- "get my expense report"

TRANSACTION examples (classify into categories):
- "I spent 500 on groceries"
- "paid 1000 for rent"
- "bought coffee for 50"
- "expense of 200 at restaurant"
- "spent 300 on gas"
- "purchased laptop for 50000"

Available categories (only use for TRANSACTIONS):
{categories_list}

Return ONLY valid JSON:
- For QUERIES: {{"category": null, "subcategory": null, "confidence": 1.0}}
- For TRANSACTIONS: {{"category": "exact match from list above", "subcategory": "exact match from list above", "confidence": 0.0-1.0}}"""

    return prompt
