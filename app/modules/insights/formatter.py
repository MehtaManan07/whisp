from datetime import datetime

from app.utils.datetime import to_user_timezone


def _pct_change(current: float, previous: float) -> str:
    if previous == 0:
        return "no prior data"
    change = ((current - previous) / previous) * 100
    if change > 0:
        return f"↑{change:.0f}% vs last period"
    elif change < 0:
        return f"↓{abs(change):.0f}% vs last period"
    return "same as last period"


def _format_amount(amount: float) -> str:
    return f"₹{amount:,.0f}" if amount == int(amount) else f"₹{amount:,.2f}"


def _bar_chart(items: list[dict], key: str, max_width: int = 5) -> list[str]:
    """Render a simple unicode bar chart."""
    if not items:
        return []
    max_val = max(i[key] for i in items) or 1
    lines = []
    for item in items:
        filled = round((item[key] / max_val) * max_width)
        bar = "█" * filled + "░" * (max_width - filled)
        lines.append(f"{item['day']:<3} {bar} {_format_amount(item[key])}")
    return lines


def format_weekly_report(data: dict, user_timezone: str = "UTC") -> str:
    start = data["period_start"]
    end = data["period_end"]
    start_str = start.strftime("%b %d")
    end_str = (end - __import__("datetime").timedelta(days=1)).strftime("%b %d, %Y")

    if data["count"] == 0:
        return (
            f"*📊 Weekly Spending Report*\n"
            f"_{start_str} – {end_str}_\n\n"
            f"No expenses recorded this week."
        )

    lines = [
        f"*📊 Weekly Spending Report*",
        f"_{start_str} – {end_str}_",
        "",
        f"*Total: {_format_amount(data['total'])}* ({_pct_change(data['total'], data['prev_total'])})",
        f"*Transactions:* {data['count']}",
    ]

    # Categories
    if data["categories"]:
        lines.append("")
        lines.append("*Top Categories*")
        for i, cat in enumerate(data["categories"][:5], 1):
            lines.append(
                f"{i}. {cat['category']} — {_format_amount(cat['total'])} ({cat['pct']}%)"
            )

    # Vendors
    if data["vendors"]:
        lines.append("")
        lines.append("*Frequent Spends*")
        vendor_parts = [f"{v['vendor']} ({v['frequency']}x)" for v in data["vendors"][:5]]
        lines.append(" · ".join(vendor_parts))

    # Biggest expense
    if data["biggest"]:
        b = data["biggest"]
        lines.append("")
        lines.append("*Biggest Expense*")
        parts = [_format_amount(b["amount"])]
        if b.get("vendor"):
            parts.append(f"at {b['vendor']}")
        if b.get("category"):
            parts.append(f"({b['category']})")
        if b.get("timestamp"):
            ts = b["timestamp"]
            if isinstance(ts, datetime):
                ts = to_user_timezone(ts, user_timezone)
                parts.append(f"on {ts.strftime('%b %d')}")
        lines.append(" ".join(parts))

    # Daily average
    lines.append("")
    lines.append(f"*Daily Avg: {_format_amount(data['daily_avg'])}*")

    return "\n".join(lines)


def format_monthly_report(data: dict, user_timezone: str = "UTC") -> str:
    start = data["period_start"]
    month_label = start.strftime("%B %Y")

    if data["count"] == 0:
        return (
            f"*📊 Monthly Spending Report*\n"
            f"_{month_label}_\n\n"
            f"No expenses recorded this month."
        )

    lines = [
        f"*📊 Monthly Spending Report*",
        f"_{month_label}_",
        "",
        f"*Total: {_format_amount(data['total'])}* ({_pct_change(data['total'], data['prev_total'])})",
        f"*Transactions:* {data['count']}",
    ]

    # Category breakdown
    if data["categories"]:
        lines.append("")
        lines.append("*Category Breakdown*")
        for i, cat in enumerate(data["categories"][:10], 1):
            lines.append(
                f"{i}. {cat['category']} — {_format_amount(cat['total'])} ({cat['pct']}%)"
            )

    # Weekly trend
    if data.get("weekly_trend"):
        lines.append("")
        lines.append("*Weekly Trend*")
        for i, w in enumerate(data["weekly_trend"], 1):
            lines.append(f"Week {i}: {_format_amount(w['total'])}")

    # Vendors
    if data["vendors"]:
        lines.append("")
        lines.append("*Top Vendors*")
        vendor_parts = [f"{v['vendor']} ({v['frequency']}x)" for v in data["vendors"][:5]]
        lines.append(" · ".join(vendor_parts))

    # Daily average comparison
    lines.append("")
    avg_line = f"*Daily Avg: {_format_amount(data['daily_avg'])}*"
    if data.get("prev_daily_avg") and data["prev_daily_avg"] > 0:
        avg_line += f" (vs {_format_amount(data['prev_daily_avg'])} last month)"
    lines.append(avg_line)

    # Day-of-week pattern
    if data.get("dow_pattern"):
        lines.append("")
        lines.append("*Spending by Day*")
        lines.extend(_bar_chart(data["dow_pattern"], "total"))

    return "\n".join(lines)


def format_on_demand_insights(data: dict, period_label: str, user_timezone: str = "UTC") -> str:
    """Format insights for on-demand chat responses. Reuses weekly/monthly formatters."""
    if "weekly_trend" in data:
        return format_monthly_report(data, user_timezone)
    return format_weekly_report(data, user_timezone)
