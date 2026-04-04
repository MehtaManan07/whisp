import logging

from app.modules.insights.analytics import AnalyticsService
from app.modules.insights.formatter import format_weekly_report, format_monthly_report

logger = logging.getLogger(__name__)


class ReportsService:
    def __init__(self):
        self.analytics = AnalyticsService()

    async def send_weekly_report(self, user, whatsapp_service) -> bool:
        """Generate and send a weekly spending report to a user."""
        user_timezone = user.timezone or "UTC"

        try:
            data = await self.analytics.get_weekly_report_data(
                user_id=user.id, user_timezone=user_timezone
            )
            message = format_weekly_report(data, user_timezone)
            await whatsapp_service.send_text(user.phone_number, message)
            logger.info(f"Weekly report sent to user {user.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send weekly report to user {user.id}: {e}")
            return False

    async def send_monthly_report(self, user, whatsapp_service) -> bool:
        """Generate and send a monthly spending report to a user."""
        user_timezone = user.timezone or "UTC"

        try:
            data = await self.analytics.get_monthly_report_data(
                user_id=user.id, user_timezone=user_timezone
            )
            message = format_monthly_report(data, user_timezone)
            await whatsapp_service.send_text(user.phone_number, message)
            logger.info(f"Monthly report sent to user {user.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send monthly report to user {user.id}: {e}")
            return False
