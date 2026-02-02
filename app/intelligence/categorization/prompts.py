"""
Prompts for category classification
"""

from typing import Optional
from .constants import CATEGORIES


def build_classification_prompt(
    original_message: str,
    vendor: Optional[str] = None,
    note: Optional[str] = None,
    amount: Optional[float] = None,
) -> str:
    """
    Build a prompt for LLM-based category classification.
    
    This is the primary classification method for expenses without known vendors.
    The LLM understands context and meaning, unlike regex patterns.
    
    Args:
        original_message: The full original user message
        vendor: Extracted vendor/merchant name (if any)
        note: Extracted description/note (if any)
        amount: Transaction amount
        
    Returns:
        Formatted prompt string for LLM classification
    """
    categories_list = "\n".join(
        [f"- {cat}: {', '.join(subcats)}" for cat, subcats in CATEGORIES.items()]
    )
    
    # Build context section
    context_parts = []
    if vendor:
        context_parts.append(f"- Vendor/Merchant: {vendor}")
    if note:
        context_parts.append(f"- Description/Note: {note}")
    if amount:
        context_parts.append(f"- Amount: ₹{amount:,.2f}")
    
    extracted_info = "\n".join(context_parts) if context_parts else "- No structured info extracted"

    prompt = f"""You are an expense categorization expert. Classify this expense into the most appropriate category and subcategory.

## ORIGINAL MESSAGE
"{original_message}"

## EXTRACTED INFO
{extracted_info}

## CRITICAL CLASSIFICATION RULES

1. **Understand context, not just words**:
   - "business" = work/professional expense → Business category
   - "training" = learning/education → Education category  
   - "bus" or "took the bus" = public transit → Transportation category
   - "spa treatment" = personal care → Personal Care category
   - "namespace" or "dispatch" = likely tech/miscellaneous, NOT spa

2. **Amount context matters**:
   - Very high amounts (>50,000) are likely rent, tuition, travel, or business expenses
   - Small amounts (<500) are likely food, transit, or small purchases
   - Use amount to validate your category choice makes sense

3. **When in doubt**:
   - If the description is vague or ambiguous, use "Other > Miscellaneous"
   - Set confidence lower (0.5-0.7) for uncertain classifications
   - Never force-fit into a category just to avoid "Other"

## AVAILABLE CATEGORIES
{categories_list}

## YOUR TASK
Analyze the FULL context of the message and return a JSON classification.

For expense transactions, return:
{{"category": "exact category name", "subcategory": "exact subcategory name", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}

For queries/non-transactions (like "show my expenses"), return:
{{"category": null, "subcategory": null, "confidence": 1.0, "reasoning": "this is a query, not an expense"}}

Return ONLY the JSON object, no other text."""

    return prompt


def build_correction_learning_prompt(
    original_message: str,
    wrong_category: str,
    wrong_subcategory: str,
    correct_category: str,
    correct_subcategory: str,
) -> str:
    """
    Build a prompt to help the LLM learn from user corrections.
    This can be used for generating better classification rules.
    
    Args:
        original_message: The original expense message
        wrong_category: The incorrectly assigned category
        wrong_subcategory: The incorrectly assigned subcategory
        correct_category: The user-corrected category
        correct_subcategory: The user-corrected subcategory
        
    Returns:
        Prompt for learning from the correction
    """
    return f"""A user corrected an expense classification. Learn from this mistake.

Original message: "{original_message}"
Wrong classification: {wrong_category} > {wrong_subcategory}
Correct classification: {correct_category} > {correct_subcategory}

Why was the original classification wrong? What pattern should we remember?
Return JSON: {{"pattern": "description of what to look for", "correct_category": "{correct_category}", "correct_subcategory": "{correct_subcategory}", "avoid_confusion_with": "{wrong_category} > {wrong_subcategory}"}}"""
