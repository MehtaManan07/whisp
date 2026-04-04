from app.intelligence.intent.base_handler import BaseHandlers
from app.intelligence.intent.decorators import intent_handler
from app.intelligence.intent.types import CLASSIFIED_RESULT, IntentType
from app.modules.insights.analytics import AnalyticsService
from app.modules.insights.formatter import format_weekly_report, format_monthly_report
from app.modules.insights.dto import GetInsightsModel


class InsightsHandlers(BaseHandlers):
    def __init__(self):
        super().__init__()
        self.analytics = AnalyticsService()

    @intent_handler(IntentType.GET_INSIGHTS)
    async def get_insights(
        self, classified_result: CLASSIFIED_RESULT, user_id: int, user_timezone: str = "UTC"
    ) -> str:
        dto, _ = classified_result
        if not dto or not isinstance(dto, GetInsightsModel):
            # Default to this week if extraction failed
            period = "this_week"
        else:
            period = dto.period or "this_week"

        if period in ("this_month", "last_month"):
            data = await self.analytics.get_monthly_report_data(user_id, user_timezone)
            if period == "last_month":
                # Swap: show last month as the primary period
                data["total"], data["prev_total"] = data["prev_total"], data["total"]
            return format_monthly_report(data, user_timezone)
        else:
            data = await self.analytics.get_weekly_report_data(user_id, user_timezone)
            if period == "last_week":
                data["total"], data["prev_total"] = data["prev_total"], data["total"]
            return format_weekly_report(data, user_timezone)
