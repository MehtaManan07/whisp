import logging
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, and_
from sqlalchemy.orm import Session, aliased

from app.core.db.engine import run_db
from app.modules.budgets.models import Budget
from app.modules.budgets.dto import CreateBudgetModel
from app.modules.budgets.formatter import format_budget_warning
from app.modules.expenses.models import Expense
from app.modules.categories.models import Category
from app.utils.datetime import utc_now

logger = logging.getLogger(__name__)



class BudgetService:

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_or_update_budget(self, data: CreateBudgetModel) -> dict:
        """Upsert: one active budget per user+category+period."""

        def _upsert(db: Session) -> dict:
            existing = db.execute(
                select(Budget).where(
                    Budget.user_id == data.user_id,
                    Budget.category_name == data.category_name,
                    Budget.period == data.period,
                    Budget.is_active == True,
                    Budget.deleted_at.is_(None),
                )
            ).scalar_one_or_none()

            if existing:
                existing.amount_limit = data.amount_limit
                existing.updated_at = utc_now()
                db.commit()
                return {"budget": existing, "action": "updated"}

            budget = Budget(
                user_id=data.user_id,
                category_name=data.category_name,
                amount_limit=data.amount_limit,
                period=data.period,
                is_active=True,
                created_at=utc_now(),
            )
            db.add(budget)
            db.commit()
            return {"budget": budget, "action": "created"}

        return await run_db(_upsert)

    async def get_active_budgets(self, user_id: int) -> list[Budget]:
        def _q(db: Session) -> list[Budget]:
            return list(
                db.execute(
                    select(Budget).where(
                        Budget.user_id == user_id,
                        Budget.is_active == True,
                        Budget.deleted_at.is_(None),
                    )
                )
                .scalars()
                .all()
            )

        return await run_db(_q)

    async def get_budgets_with_status(
        self, user_id: int, user_timezone: str = "UTC"
    ) -> list[dict]:
        """Fetch all active budgets and compute current spend for each. Single session."""

        def _build(db: Session) -> list[dict]:
            budgets = list(
                db.execute(
                    select(Budget).where(
                        Budget.user_id == user_id,
                        Budget.is_active == True,
                        Budget.deleted_at.is_(None),
                    )
                )
                .scalars()
                .all()
            )

            if not budgets:
                return []

            results = []
            for b in budgets:
                start, end, days_left = self._period_bounds(b.period, user_timezone)
                spend = self._category_spend_sync(db, user_id, b.category_name, start, end)
                remaining = max(b.amount_limit - spend, 0)
                pct = (spend / b.amount_limit * 100) if b.amount_limit > 0 else 0

                results.append(
                    {
                        "category_name": b.category_name,
                        "amount_limit": b.amount_limit,
                        "period": b.period,
                        "current_spend": spend,
                        "pct_used": round(pct, 1),
                        "remaining": remaining,
                        "days_left": days_left,
                    }
                )

            return results

        return await run_db(_build)

    # ------------------------------------------------------------------
    # Spending window analysis
    # ------------------------------------------------------------------

    async def get_spending_windows(
        self, user_id: int, category_name: str, user_timezone: str, cache_service
    ) -> list[dict]:
        """Get danger windows for a category. Cached for 7 days."""
        cache_key = f"budget_windows:{user_id}:{category_name}"
        cached = await cache_service.get_key(cache_key)
        if cached:
            return cached

        def _analyze(db: Session) -> list[dict]:
            return self._get_spending_windows_sync(db, user_id, category_name, user_timezone)

        windows = await run_db(_analyze)

        # No defaults — proactive warnings only work once real patterns exist
        await cache_service.set_key(cache_key, windows, ttl=604800)  # 7 days
        return windows

    def _get_spending_windows_sync(
        self, db: Session, user_id: int, category_name: str, user_timezone: str
    ) -> list[dict]:
        """GROUP BY hour + day-of-week over last 90 days. Returns danger windows."""
        tz = ZoneInfo(user_timezone)
        offset_seconds = int(datetime.now(tz).utcoffset().total_seconds())
        # SQLite modifier format: "+N hours", "+N minutes"
        offset_hours = offset_seconds // 3600
        offset_mins = (offset_seconds % 3600) // 60

        modifiers = []
        if offset_hours:
            modifiers.append(f"{offset_hours:+d} hours")
        if offset_mins:
            modifiers.append(f"{offset_mins:+d} minutes")

        start = utc_now() - timedelta(days=90)

        SubCat = aliased(Category, name="subcat")
        ParentCat = aliased(Category, name="parent")

        # Build strftime with timezone modifiers
        hour_expr = Expense.timestamp
        dow_expr = Expense.timestamp
        for mod in modifiers:
            hour_expr = func.strftime("%H", hour_expr, mod)
            dow_expr = func.strftime("%w", dow_expr, mod)
        else:
            if not modifiers:
                hour_expr = func.strftime("%H", Expense.timestamp)
                dow_expr = func.strftime("%w", Expense.timestamp)

        rows = db.execute(
            select(
                hour_expr.label("hour"),
                dow_expr.label("dow"),
                func.count().label("count"),
            )
            .join(SubCat, Expense.category_id == SubCat.id, isouter=True)
            .join(ParentCat, SubCat.parent_id == ParentCat.id, isouter=True)
            .where(
                Expense.user_id == user_id,
                Expense.deleted_at.is_(None),
                Expense.timestamp >= start,
                func.coalesce(ParentCat.name, SubCat.name) == category_name,
            )
            .group_by("hour", "dow")
            .order_by(func.count().desc())
        ).all()

        if not rows:
            return []

        avg_count = sum(r.count for r in rows) / len(rows)
        threshold = max(avg_count * 1.5, 2)  # At least 2 transactions to be a pattern

        return [
            {"hour": int(r.hour), "dow": str(r.dow)}
            for r in rows
            if r.count >= threshold
        ]

    # ------------------------------------------------------------------
    # Proactive warning check
    # ------------------------------------------------------------------

    async def check_and_warn_user(self, user, whatsapp_service, cache_service) -> int:
        """Check all budgets for a user, send warnings if approaching limit before spending window."""
        user_timezone = user.timezone or "UTC"
        tz = ZoneInfo(user_timezone)
        now_local = datetime.now(tz)
        current_hour = now_local.hour
        current_dow = str(now_local.strftime("%w"))  # 0=Sun

        budgets = await self.get_active_budgets(user.id)
        if not budgets:
            return 0

        warnings_sent = 0

        for budget in budgets:
            today_str = now_local.strftime("%Y-%m-%d")
            spam_key = f"budget_warned:{user.id}:{budget.id}:{today_str}"

            already_warned = await cache_service.exists(spam_key)
            if already_warned:
                continue

            windows = await self.get_spending_windows(
                user.id, budget.category_name, user_timezone, cache_service
            )

            if not self._is_before_danger_window(current_hour, current_dow, windows):
                continue

            # Check current spend vs limit
            start, end, days_left = self._period_bounds(budget.period, user_timezone)

            def _get_spend(db: Session, s=start, e=end) -> float:
                return self._category_spend_sync(db, user.id, budget.category_name, s, e)

            current_spend = await run_db(_get_spend)
            pct = (current_spend / budget.amount_limit * 100) if budget.amount_limit > 0 else 0

            if pct < 70:
                continue

            message = format_budget_warning(
                category=budget.category_name,
                current_spend=current_spend,
                limit=budget.amount_limit,
                period=budget.period,
                days_left=days_left,
            )

            try:
                await whatsapp_service.send_text(user.phone_number, message)
                await cache_service.set_key(spam_key, "1", ttl=86400)
                warnings_sent += 1
                logger.info(
                    "Budget warning sent: user=%s budget=%s pct=%.0f%%",
                    user.id, budget.category_name, pct,
                )
            except Exception as e:
                logger.error("Failed to send budget warning: user=%s error=%s", user.id, e)

        return warnings_sent

    def _is_before_danger_window(
        self, current_hour: int, current_dow: str, windows: list[dict]
    ) -> bool:
        """Check if current time is 1-2 hours before any danger window."""
        for w in windows:
            w_dow = str(w.get("dow", "*"))
            if w_dow != "*" and w_dow != current_dow:
                continue
            w_hour = w["hour"]
            # Trigger 1-2 hours before the danger window
            if w_hour - 2 <= current_hour <= w_hour - 1:
                return True
        return False

    # ------------------------------------------------------------------
    # Sync helpers
    # ------------------------------------------------------------------

    def _category_spend_sync(
        self, db: Session, user_id: int, category_name: str, start: datetime, end: datetime
    ) -> float:
        """Get total spend for a parent category in a date range."""
        SubCat = aliased(Category, name="subcat")
        ParentCat = aliased(Category, name="parent")

        result = db.execute(
            select(func.coalesce(func.sum(Expense.amount), 0.0))
            .join(SubCat, Expense.category_id == SubCat.id, isouter=True)
            .join(ParentCat, SubCat.parent_id == ParentCat.id, isouter=True)
            .where(
                Expense.user_id == user_id,
                Expense.deleted_at.is_(None),
                Expense.timestamp >= start,
                Expense.timestamp < end,
                func.coalesce(ParentCat.name, SubCat.name) == category_name,
            )
        )
        return float(result.scalar())

    def _period_bounds(
        self, period: str, user_timezone: str
    ) -> tuple[datetime, datetime, int]:
        """Get start, end, and days_left for current period."""
        tz = ZoneInfo(user_timezone)
        now_local = datetime.now(tz)

        if period == "weekly":
            days_since_monday = now_local.weekday()
            start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
                days=days_since_monday
            )
            end_local = start_local + timedelta(days=7)
        else:  # monthly
            start_local = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start_local.month == 12:
                end_local = start_local.replace(year=start_local.year + 1, month=1)
            else:
                end_local = start_local.replace(month=start_local.month + 1)

        days_left = max((end_local - now_local).days, 0)

        return (
            start_local.astimezone(timezone.utc),
            end_local.astimezone(timezone.utc),
            days_left,
        )
