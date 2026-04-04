def _format_amount(amount: float) -> str:
    return f"₹{amount:,.0f}" if amount == int(amount) else f"₹{amount:,.2f}"


# Category-specific tips for proactive warnings
_CATEGORY_TIPS = {
    "Food & Dining": "Tonight might be a good night to cook.",
    "Transportation": "Consider public transit or walking today.",
    "Shopping": "Maybe hold off on that cart for now.",
    "Entertainment": "A quiet night in could save some cash.",
    "Personal Care": "Skip the impulse salon visit today.",
    "Bills & Utilities": "Check if any subscriptions can be paused.",
}
_DEFAULT_TIP = "Consider holding off on non-essentials."


def format_budget_warning(
    category: str,
    current_spend: float,
    limit: float,
    period: str,
    days_left: int,
) -> str:
    pct = (current_spend / limit) * 100 if limit > 0 else 0
    period_label = "this month" if period == "monthly" else "this week"
    tip = _CATEGORY_TIPS.get(category, _DEFAULT_TIP)

    return (
        f"💸 *Budget Alert: {category}*\n\n"
        f"You've spent {_format_amount(current_spend)} on {category.lower()} "
        f"{period_label} ({pct:.0f}% of your {_format_amount(limit)} limit) "
        f"with {days_left} day{'s' if days_left != 1 else ''} left.\n\n"
        f"💡 {tip}"
    )


def format_budget_list(budgets: list[dict]) -> str:
    """Format budget list with progress bars. Each dict has: category_name, amount_limit, period, current_spend, pct_used, remaining, days_left."""
    if not budgets:
        return "You haven't set any budgets yet.\nTry: \"max 5000 on food per month\""

    lines = ["*📋 Your Active Budgets*"]

    for b in budgets:
        pct = b["pct_used"]
        emoji = "🟢" if pct < 70 else "🟡" if pct < 90 else "🔴"
        filled = min(round(pct / 20), 5)
        bar = "█" * filled + "░" * (5 - filled)

        lines.append(
            f"\n{emoji} *{b['category_name']}* ({b['period']})\n"
            f"   {bar} {pct:.0f}% used\n"
            f"   {_format_amount(b['current_spend'])} / {_format_amount(b['amount_limit'])} "
            f"— {_format_amount(b['remaining'])} left ({b['days_left']}d)"
        )

    return "\n".join(lines)


def format_budget_set_confirmation(category: str, limit: float, period: str) -> str:
    return (
        f"✅ Budget set: {_format_amount(limit)} on *{category}* per {period.rstrip('ly')}.\n"
        f"I'll warn you when you're approaching your limit."
    )
