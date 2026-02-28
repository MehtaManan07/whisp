"""
Run deterministic query filter regression checks.

Usage:
    python -m scripts.run_query_filter_regression
"""

from app.intelligence.categorization.query_mapper import resolve_query_category_aliases


CASES = [
    {
        "query": "show me all food expenses in last 5 days",
        "expected_category": "Food & Dining",
        "expected_subcategory": None,
    },
    {
        "query": "show grocery expenses for this week",
        "expected_category": "Food & Dining",
        "expected_subcategory": "Groceries",
    },
    {
        "query": "show restarant expenses in last month",
        "expected_category": "Food & Dining",
        "expected_subcategory": "Restaurants",
    },
    {
        "query": "show groceris spend",
        "expected_category": "Food & Dining",
        "expected_subcategory": "Groceries",
    },
    {
        "query": "show my transport expenses",
        "expected_category": "Transportation",
        "expected_subcategory": None,
    },
]


def main() -> None:
    passed = 0
    print("Running deterministic query filter regression checks...\n")

    for idx, case in enumerate(CASES, start=1):
        result = resolve_query_category_aliases(case["query"])
        ok = (
            result["category_name"] == case["expected_category"]
            and result["subcategory_name"] == case["expected_subcategory"]
        )
        status = "PASS" if ok else "FAIL"
        print(
            f"{idx}. {status} | query='{case['query']}' | "
            f"got=({result['category_name']}, {result['subcategory_name']}) "
            f"score={result['alias_score']:.3f}"
        )
        if ok:
            passed += 1

    total = len(CASES)
    print(f"\nSummary: {passed}/{total} passed")
    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
