import logging
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db.engine import run_db
from app.modules.expenses.models import Expense
from app.modules.categories.models import Category

logger = logging.getLogger(__name__)


class AnalyticsService:

    # ------------------------------------------------------------------
    # Primitive query methods
    # ------------------------------------------------------------------

    async def get_period_total(
        self, user_id: int, start: datetime, end: datetime
    ) -> float:
        def _q(db: Session) -> float:
            result = db.execute(
                select(func.coalesce(func.sum(Expense.amount), 0.0)).where(
                    Expense.user_id == user_id,
                    Expense.deleted_at.is_(None),
                    Expense.timestamp >= start,
                    Expense.timestamp < end,
                )
            )
            return float(result.scalar())

        return await run_db(_q)

    async def get_expense_count(
        self, user_id: int, start: datetime, end: datetime
    ) -> int:
        def _q(db: Session) -> int:
            result = db.execute(
                select(func.count()).where(
                    Expense.user_id == user_id,
                    Expense.deleted_at.is_(None),
                    Expense.timestamp >= start,
                    Expense.timestamp < end,
                )
            )
            return int(result.scalar())

        return await run_db(_q)

    async def get_category_breakdown(
        self, user_id: int, start: datetime, end: datetime, limit: int | None = None
    ) -> list[dict]:
        """Group expenses by parent category, return total + count + pct."""

        def _q(db: Session) -> list[dict]:
            from sqlalchemy.orm import aliased

            SubCat = aliased(Category, name="subcat")
            ParentCat = aliased(Category, name="parent")

            # Join: expense -> subcategory -> parent category
            # COALESCE(parent.name, subcat.name) gives us the top-level group
            stmt = (
                select(
                    func.coalesce(ParentCat.name, SubCat.name).label("category"),
                    func.sum(Expense.amount).label("total"),
                    func.count().label("count"),
                )
                .join(SubCat, Expense.category_id == SubCat.id, isouter=True)
                .join(ParentCat, SubCat.parent_id == ParentCat.id, isouter=True)
                .where(
                    Expense.user_id == user_id,
                    Expense.deleted_at.is_(None),
                    Expense.timestamp >= start,
                    Expense.timestamp < end,
                )
                .group_by("category")
                .order_by(func.sum(Expense.amount).desc())
            )

            if limit:
                stmt = stmt.limit(limit)

            rows = db.execute(stmt).all()
            grand_total = sum(r.total for r in rows) or 1
            return [
                {
                    "category": r.category or "Uncategorized",
                    "total": float(r.total),
                    "count": int(r.count),
                    "pct": round(r.total / grand_total * 100, 1),
                }
                for r in rows
            ]

        return await run_db(_q)

    async def get_top_vendors(
        self, user_id: int, start: datetime, end: datetime, limit: int = 5
    ) -> list[dict]:
        def _q(db: Session) -> list[dict]:
            rows = db.execute(
                select(
                    Expense.vendor,
                    func.count().label("frequency"),
                    func.sum(Expense.amount).label("total"),
                )
                .where(
                    Expense.user_id == user_id,
                    Expense.deleted_at.is_(None),
                    Expense.vendor.isnot(None),
                    Expense.timestamp >= start,
                    Expense.timestamp < end,
                )
                .group_by(Expense.vendor)
                .order_by(func.count().desc())
                .limit(limit)
            ).all()
            return [
                {
                    "vendor": r.vendor,
                    "frequency": int(r.frequency),
                    "total": float(r.total),
                }
                for r in rows
            ]

        return await run_db(_q)

    async def get_biggest_expense(
        self, user_id: int, start: datetime, end: datetime
    ) -> dict | None:
        def _q(db: Session) -> dict | None:
            from sqlalchemy.orm import aliased, selectinload

            SubCat = aliased(Category, name="subcat")
            ParentCat = aliased(Category, name="parent")

            row = db.execute(
                select(
                    Expense.amount,
                    Expense.vendor,
                    Expense.timestamp,
                    Expense.note,
                    func.coalesce(ParentCat.name, SubCat.name).label("category"),
                )
                .join(SubCat, Expense.category_id == SubCat.id, isouter=True)
                .join(ParentCat, SubCat.parent_id == ParentCat.id, isouter=True)
                .where(
                    Expense.user_id == user_id,
                    Expense.deleted_at.is_(None),
                    Expense.timestamp >= start,
                    Expense.timestamp < end,
                )
                .order_by(Expense.amount.desc())
                .limit(1)
            ).first()

            if not row:
                return None

            return {
                "amount": float(row.amount),
                "vendor": row.vendor,
                "category": row.category,
                "timestamp": row.timestamp,
                "note": row.note,
            }

        return await run_db(_q)

    async def get_day_of_week_pattern(
        self, user_id: int, start: datetime, end: datetime
    ) -> list[dict]:
        """Returns spending by day-of-week (0=Sun … 6=Sat in SQLite)."""

        def _q(db: Session) -> list[dict]:
            dow = func.strftime("%w", Expense.timestamp)
            rows = db.execute(
                select(
                    dow.label("dow"),
                    func.sum(Expense.amount).label("total"),
                    func.count().label("count"),
                )
                .where(
                    Expense.user_id == user_id,
                    Expense.deleted_at.is_(None),
                    Expense.timestamp >= start,
                    Expense.timestamp < end,
                )
                .group_by(dow)
                .order_by(dow)
            ).all()

            day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
            return [
                {
                    "day": day_names[int(r.dow)],
                    "total": float(r.total),
                    "count": int(r.count),
                }
                for r in rows
            ]

        return await run_db(_q)

    async def get_weekly_trend(
        self, user_id: int, start: datetime, end: datetime
    ) -> list[dict]:
        """Weekly totals within a period (for monthly report)."""

        def _q(db: Session) -> list[dict]:
            week = func.strftime("%W", Expense.timestamp)
            rows = db.execute(
                select(
                    week.label("week_num"),
                    func.sum(Expense.amount).label("total"),
                    func.count().label("count"),
                )
                .where(
                    Expense.user_id == user_id,
                    Expense.deleted_at.is_(None),
                    Expense.timestamp >= start,
                    Expense.timestamp < end,
                )
                .group_by(week)
                .order_by(week)
            ).all()
            return [
                {
                    "week": int(r.week_num),
                    "total": float(r.total),
                    "count": int(r.count),
                }
                for r in rows
            ]

        return await run_db(_q)

    # ------------------------------------------------------------------
    # Orchestration: assemble full report data
    # ------------------------------------------------------------------

    def _week_boundaries(self, tz: ZoneInfo) -> tuple[datetime, datetime, datetime, datetime]:
        """Return (this_week_start, this_week_end, last_week_start, last_week_end) in UTC."""
        now_local = datetime.now(tz)
        # Monday = start of week
        days_since_monday = now_local.weekday()
        this_week_start = now_local.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=days_since_monday)
        this_week_end = this_week_start + timedelta(days=7)
        last_week_start = this_week_start - timedelta(days=7)
        last_week_end = this_week_start

        return (
            this_week_start.astimezone(timezone.utc),
            this_week_end.astimezone(timezone.utc),
            last_week_start.astimezone(timezone.utc),
            last_week_end.astimezone(timezone.utc),
        )

    def _month_boundaries(self, tz: ZoneInfo) -> tuple[datetime, datetime, datetime, datetime]:
        """Return (this_month_start, this_month_end, last_month_start, last_month_end) in UTC."""
        now_local = datetime.now(tz)
        this_month_start = now_local.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        # Next month start
        if this_month_start.month == 12:
            this_month_end = this_month_start.replace(year=this_month_start.year + 1, month=1)
        else:
            this_month_end = this_month_start.replace(month=this_month_start.month + 1)

        # Last month
        last_month_end = this_month_start
        if this_month_start.month == 1:
            last_month_start = this_month_start.replace(year=this_month_start.year - 1, month=12)
        else:
            last_month_start = this_month_start.replace(month=this_month_start.month - 1)

        return (
            this_month_start.astimezone(timezone.utc),
            this_month_end.astimezone(timezone.utc),
            last_month_start.astimezone(timezone.utc),
            last_month_end.astimezone(timezone.utc),
        )

    # ------------------------------------------------------------------
    # Sync query helpers (called within a single session)
    # ------------------------------------------------------------------

    def _total_and_count(
        self, db: Session, user_id: int, start: datetime, end: datetime
    ) -> tuple[float, int]:
        """SUM + COUNT in one query instead of two round-trips."""
        row = db.execute(
            select(
                func.coalesce(func.sum(Expense.amount), 0.0).label("total"),
                func.count().label("count"),
            ).where(
                Expense.user_id == user_id,
                Expense.deleted_at.is_(None),
                Expense.timestamp >= start,
                Expense.timestamp < end,
            )
        ).one()
        return float(row.total), int(row.count)

    def _prev_total(
        self, db: Session, user_id: int, start: datetime, end: datetime
    ) -> float:
        result = db.execute(
            select(func.coalesce(func.sum(Expense.amount), 0.0)).where(
                Expense.user_id == user_id,
                Expense.deleted_at.is_(None),
                Expense.timestamp >= start,
                Expense.timestamp < end,
            )
        )
        return float(result.scalar())

    def _category_breakdown_sync(
        self, db: Session, user_id: int, start: datetime, end: datetime, limit: int | None = None
    ) -> list[dict]:
        from sqlalchemy.orm import aliased

        SubCat = aliased(Category, name="subcat")
        ParentCat = aliased(Category, name="parent")

        stmt = (
            select(
                func.coalesce(ParentCat.name, SubCat.name).label("category"),
                func.sum(Expense.amount).label("total"),
                func.count().label("count"),
            )
            .join(SubCat, Expense.category_id == SubCat.id, isouter=True)
            .join(ParentCat, SubCat.parent_id == ParentCat.id, isouter=True)
            .where(
                Expense.user_id == user_id,
                Expense.deleted_at.is_(None),
                Expense.timestamp >= start,
                Expense.timestamp < end,
            )
            .group_by("category")
            .order_by(func.sum(Expense.amount).desc())
        )
        if limit:
            stmt = stmt.limit(limit)

        rows = db.execute(stmt).all()
        grand_total = sum(r.total for r in rows) or 1
        return [
            {
                "category": r.category or "Uncategorized",
                "total": float(r.total),
                "count": int(r.count),
                "pct": round(r.total / grand_total * 100, 1),
            }
            for r in rows
        ]

    def _top_vendors_sync(
        self, db: Session, user_id: int, start: datetime, end: datetime, limit: int = 5
    ) -> list[dict]:
        rows = db.execute(
            select(
                Expense.vendor,
                func.count().label("frequency"),
                func.sum(Expense.amount).label("total"),
            )
            .where(
                Expense.user_id == user_id,
                Expense.deleted_at.is_(None),
                Expense.vendor.isnot(None),
                Expense.timestamp >= start,
                Expense.timestamp < end,
            )
            .group_by(Expense.vendor)
            .order_by(func.count().desc())
            .limit(limit)
        ).all()
        return [
            {"vendor": r.vendor, "frequency": int(r.frequency), "total": float(r.total)}
            for r in rows
        ]

    def _biggest_expense_sync(
        self, db: Session, user_id: int, start: datetime, end: datetime
    ) -> dict | None:
        from sqlalchemy.orm import aliased

        SubCat = aliased(Category, name="subcat")
        ParentCat = aliased(Category, name="parent")

        row = db.execute(
            select(
                Expense.amount,
                Expense.vendor,
                Expense.timestamp,
                Expense.note,
                func.coalesce(ParentCat.name, SubCat.name).label("category"),
            )
            .join(SubCat, Expense.category_id == SubCat.id, isouter=True)
            .join(ParentCat, SubCat.parent_id == ParentCat.id, isouter=True)
            .where(
                Expense.user_id == user_id,
                Expense.deleted_at.is_(None),
                Expense.timestamp >= start,
                Expense.timestamp < end,
            )
            .order_by(Expense.amount.desc())
            .limit(1)
        ).first()

        if not row:
            return None
        return {
            "amount": float(row.amount),
            "vendor": row.vendor,
            "category": row.category,
            "timestamp": row.timestamp,
            "note": row.note,
        }

    def _weekly_trend_sync(
        self, db: Session, user_id: int, start: datetime, end: datetime
    ) -> list[dict]:
        week = func.strftime("%W", Expense.timestamp)
        rows = db.execute(
            select(
                week.label("week_num"),
                func.sum(Expense.amount).label("total"),
                func.count().label("count"),
            )
            .where(
                Expense.user_id == user_id,
                Expense.deleted_at.is_(None),
                Expense.timestamp >= start,
                Expense.timestamp < end,
            )
            .group_by(week)
            .order_by(week)
        ).all()
        return [
            {"week": int(r.week_num), "total": float(r.total), "count": int(r.count)}
            for r in rows
        ]

    def _dow_pattern_sync(
        self, db: Session, user_id: int, start: datetime, end: datetime
    ) -> list[dict]:
        dow = func.strftime("%w", Expense.timestamp)
        rows = db.execute(
            select(
                dow.label("dow"),
                func.sum(Expense.amount).label("total"),
                func.count().label("count"),
            )
            .where(
                Expense.user_id == user_id,
                Expense.deleted_at.is_(None),
                Expense.timestamp >= start,
                Expense.timestamp < end,
            )
            .group_by(dow)
            .order_by(dow)
        ).all()
        day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        return [
            {"day": day_names[int(r.dow)], "total": float(r.total), "count": int(r.count)}
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Orchestration: single session, all queries back-to-back
    # ------------------------------------------------------------------

    async def get_weekly_report_data(self, user_id: int, user_timezone: str = "UTC") -> dict:
        tz = ZoneInfo(user_timezone)
        tw_start, tw_end, lw_start, lw_end = self._week_boundaries(tz)

        def _build(db: Session) -> dict:
            this_total, count = self._total_and_count(db, user_id, tw_start, tw_end)
            prev_total = self._prev_total(db, user_id, lw_start, lw_end)
            categories = self._category_breakdown_sync(db, user_id, tw_start, tw_end, limit=5)
            vendors = self._top_vendors_sync(db, user_id, tw_start, tw_end, limit=5)
            biggest = self._biggest_expense_sync(db, user_id, tw_start, tw_end)

            days_elapsed = max((datetime.now(tz) - tw_start.astimezone(tz)).days, 1)
            daily_avg = this_total / days_elapsed if this_total else 0.0

            return {
                "period_start": tw_start.astimezone(tz),
                "period_end": tw_end.astimezone(tz),
                "total": this_total,
                "prev_total": prev_total,
                "count": count,
                "categories": categories,
                "vendors": vendors,
                "biggest": biggest,
                "daily_avg": daily_avg,
            }

        return await run_db(_build)

    async def get_monthly_report_data(self, user_id: int, user_timezone: str = "UTC") -> dict:
        tz = ZoneInfo(user_timezone)
        tm_start, tm_end, lm_start, lm_end = self._month_boundaries(tz)

        def _build(db: Session) -> dict:
            this_total, count = self._total_and_count(db, user_id, tm_start, tm_end)
            prev_total = self._prev_total(db, user_id, lm_start, lm_end)
            categories = self._category_breakdown_sync(db, user_id, tm_start, tm_end, limit=10)
            vendors = self._top_vendors_sync(db, user_id, tm_start, tm_end, limit=5)
            biggest = self._biggest_expense_sync(db, user_id, tm_start, tm_end)
            weekly_trend = self._weekly_trend_sync(db, user_id, tm_start, tm_end)
            dow_pattern = self._dow_pattern_sync(db, user_id, tm_start, tm_end)

            last_month_days = max((lm_end - lm_start).days, 1)
            prev_daily_avg = prev_total / last_month_days if prev_total else 0.0
            days_elapsed = max((datetime.now(tz) - tm_start.astimezone(tz)).days, 1)
            daily_avg = this_total / days_elapsed if this_total else 0.0

            return {
                "period_start": tm_start.astimezone(tz),
                "period_end": tm_end.astimezone(tz),
                "total": this_total,
                "prev_total": prev_total,
                "count": count,
                "categories": categories,
                "vendors": vendors,
                "biggest": biggest,
                "weekly_trend": weekly_trend,
                "dow_pattern": dow_pattern,
                "daily_avg": daily_avg,
                "prev_daily_avg": prev_daily_avg,
            }

        return await run_db(_build)
