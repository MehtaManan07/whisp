"""
Deterministic query category/subcategory mapping.

This module provides a fast, bounded alias index to map free-text search queries
to canonical category filters before any LLM fallback is attempted.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Optional, TypedDict

from .constants import CATEGORIES, get_category_for_subcategory, is_valid_category


CATEGORY_CONFIDENCE_THRESHOLD = 0.78
SUBCATEGORY_CONFIDENCE_THRESHOLD = 0.86


class QueryAliasResult(TypedDict):
    category_name: Optional[str]
    subcategory_name: Optional[str]
    category_confidence: float
    subcategory_confidence: float
    alias_score: float
    matched_alias: Optional[str]
    match_layer: str
    reasoning: str


CATEGORY_ALIASES: dict[str, tuple[str, ...]] = {
    "Food & Dining": ("food", "foods", "eat", "eating", "meal", "meals", "dining"),
    "Transportation": ("transport", "travel commute", "commute", "rides", "ride"),
    "Shopping": ("shopping", "purchase", "purchases", "bought", "buying"),
    "Bills & Utilities": ("bills", "utilities", "bill payment", "monthly bills"),
    "Entertainment": ("entertainment", "fun", "leisure", "movies and shows"),
    "Healthcare": ("healthcare", "medical", "doctor", "medicine"),
    "Education": ("education", "learning", "study", "courses"),
    "Travel": ("trip", "travel", "vacation", "holiday"),
    "Personal Care": ("personal care", "self care", "grooming"),
    "Business": ("business", "work expenses", "office spending"),
    "Investments": ("investment", "investments", "investing"),
    "Gifts & Donations": ("gifts", "gift", "charity", "donation", "donations"),
    "Other": ("other", "misc", "miscellaneous"),
}


SUBCATEGORY_ALIASES: dict[str, tuple[str, ...]] = {
    "Groceries": ("grocery", "groceries", "supermarket", "grocery store"),
    "Restaurants": ("restaurant", "restaurants", "dining out", "dinner out", "eating out"),
    "Cafe/Coffee": ("coffee", "cafe", "cafes", "tea", "coffee shop"),
    "Food Delivery": ("delivery", "food delivery", "ordered in", "swiggy", "zomato"),
    "Ride Share": ("uber", "ola", "lyft", "rideshare", "ride share", "cab"),
    "Fuel": ("fuel", "petrol", "gas", "diesel"),
    "Public Transit": ("metro", "bus", "train", "public transit"),
    "Online Shopping": ("online shopping", "online order", "amazon", "flipkart"),
    "Rent/Mortgage": ("rent", "mortgage", "house rent"),
    "Internet": ("internet", "wifi", "broadband"),
    "Phone": ("phone bill", "mobile bill", "recharge"),
    "Streaming": ("streaming", "netflix", "prime video", "hotstar", "spotify"),
}


def _normalize_text(value: str) -> str:
    normalized = value.lower()
    normalized = re.sub(r"[^a-z0-9\s/&]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _fuzzy_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _is_plausible_token_match(alias_token: str, candidate_token: str) -> bool:
    """Guardrail to prevent unrelated fuzzy token matches."""
    if alias_token == candidate_token:
        return True
    if not alias_token or not candidate_token:
        return False
    if alias_token[0] != candidate_token[0]:
        return False
    return abs(len(alias_token) - len(candidate_token)) <= 2


def _best_match_score(normalized_text: str, alias: str) -> float:
    # Exact phrase match should always win.
    padded_text = f" {normalized_text} "
    padded_alias = f" {alias} "
    if padded_alias in padded_text:
        return 1.0

    text_tokens = normalized_text.split()
    alias_tokens = alias.split()
    if not text_tokens or not alias_tokens:
        return 0.0

    alias_len = len(alias_tokens)
    best = 0.0

    # Compare alias to token windows around alias length.
    window_sizes = {max(1, alias_len - 1), alias_len, alias_len + 1}
    if alias_len == 1:
        window_sizes = {1}
    for size in window_sizes:
        if size > len(text_tokens):
            continue
        for idx in range(0, len(text_tokens) - size + 1):
            window = " ".join(text_tokens[idx : idx + size])
            if alias_len == 1 and size == 1:
                if not _is_plausible_token_match(alias_tokens[0], text_tokens[idx]):
                    continue
            best = max(best, _fuzzy_ratio(alias, window))

    # Single-token aliases can also be compared against each individual token.
    if alias_len == 1:
        token_scores = []
        for token in text_tokens:
            if _is_plausible_token_match(alias_tokens[0], token):
                token_scores.append(_fuzzy_ratio(alias, token))
        best = max(best, max(token_scores, default=0.0))

    return best


def _match_alias_group(
    normalized_text: str,
    alias_map: dict[str, tuple[str, ...]],
) -> tuple[Optional[str], Optional[str], float]:
    best_target: Optional[str] = None
    best_alias: Optional[str] = None
    best_score = 0.0

    for target, aliases in alias_map.items():
        for alias in aliases:
            normalized_alias = _normalize_text(alias)
            score = _best_match_score(normalized_text, normalized_alias)
            if score > best_score:
                best_target = target
                best_alias = alias
                best_score = score
            elif score == best_score and best_alias is not None:
                # Deterministic tie-breaker: prefer longer aliases, then lexical order.
                if len(alias) > len(best_alias) or (len(alias) == len(best_alias) and alias < best_alias):
                    best_target = target
                    best_alias = alias
                    best_score = score

    return best_target, best_alias, best_score


def resolve_query_category_aliases(message: str) -> QueryAliasResult:
    """
    Resolve category filters for expense search using deterministic alias matching.

    Subcategory detection has a stricter threshold than category detection to avoid
    accidental narrowing for broad intents (for example, "food" should not imply
    "Groceries").
    """
    normalized = _normalize_text(message)
    if not normalized:
        return QueryAliasResult(
            category_name=None,
            subcategory_name=None,
            category_confidence=0.0,
            subcategory_confidence=0.0,
            alias_score=0.0,
            matched_alias=None,
            match_layer="alias",
            reasoning="empty query text",
        )

    subcategory, sub_alias, sub_score = _match_alias_group(normalized, SUBCATEGORY_ALIASES)
    if subcategory and sub_score >= SUBCATEGORY_CONFIDENCE_THRESHOLD:
        parent_category = get_category_for_subcategory(subcategory)
        if parent_category and is_valid_category(parent_category, subcategory):
            return QueryAliasResult(
                category_name=parent_category,
                subcategory_name=subcategory,
                category_confidence=sub_score,
                subcategory_confidence=sub_score,
                alias_score=sub_score,
                matched_alias=sub_alias,
                match_layer="alias",
                reasoning=f"matched explicit subcategory alias '{sub_alias}'",
            )

    category, cat_alias, cat_score = _match_alias_group(normalized, CATEGORY_ALIASES)
    if category and cat_score >= CATEGORY_CONFIDENCE_THRESHOLD:
        return QueryAliasResult(
            category_name=category,
            subcategory_name=None,
            category_confidence=cat_score,
            subcategory_confidence=0.0,
            alias_score=cat_score,
            matched_alias=cat_alias,
            match_layer="alias",
            reasoning=f"matched broad category alias '{cat_alias}'",
        )

    return QueryAliasResult(
        category_name=None,
        subcategory_name=None,
        category_confidence=cat_score,
        subcategory_confidence=sub_score,
        alias_score=max(cat_score, sub_score),
        matched_alias=cat_alias if cat_score >= sub_score else sub_alias,
        match_layer="alias",
        reasoning="no deterministic alias matched threshold",
    )
