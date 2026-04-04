"""
Background jobs for the scheduler.
These functions run outside of request context and call self-managing services.
"""

import logging

logger = logging.getLogger(__name__)


async def process_due_reminders() -> dict:
    """
    Process all due reminders.

    This job runs periodically to check for reminders that are due
    and sends WhatsApp notifications for each one.

    Returns:
        Summary of processed reminders
    """
    from app.core.dependencies import (
        get_whatsapp_service,
        get_reminder_service,
    )

    whatsapp_service = get_whatsapp_service()
    reminder_service = get_reminder_service()

    processed_count = 0
    error_count = 0

    logger.debug("Starting due reminders processing job")

    try:
        due_items = await reminder_service.get_due_reminders_with_users()

        if not due_items:
            logger.debug("No due reminders found")
            return {"processed": 0, "errors": 0}

        logger.info(f"Found {len(due_items)} due reminders")

        for reminder, user in due_items:
            try:
                result = await reminder_service.process_single_reminder(
                    reminder_id=reminder.id,
                    whatsapp_service=whatsapp_service,
                    reminder=reminder,
                    user=user,
                )

                if result.get("status") == "success":
                    processed_count += 1
                else:
                    error_count += 1
                    logger.warning(
                        f"Failed to process reminder {reminder.id}: {result.get('message')}"
                    )

            except Exception as e:
                error_count += 1
                logger.error(f"Error processing reminder {reminder.id}: {e}")

        logger.info(
            f"Reminders job completed: {processed_count} processed, {error_count} errors"
        )

    except Exception as e:
        logger.error(f"Error in reminders job: {e}")
        return {"processed": 0, "errors": 1, "error": str(e)}

    return {"processed": processed_count, "errors": error_count}


async def send_weekly_reports() -> dict:
    """Send weekly spending report to all active users. Runs Sunday 9 PM IST."""
    from app.core.dependencies import get_whatsapp_service, get_user_service
    from app.modules.insights.reports import ReportsService

    whatsapp_service = get_whatsapp_service()
    user_service = get_user_service()
    reports_service = ReportsService()

    logger.info("Starting weekly reports job")

    try:
        users = await user_service.get_all_users()
        sent = 0
        errors = 0

        for user in users:
            if not user.phone_number:
                continue
            success = await reports_service.send_weekly_report(user, whatsapp_service)
            if success:
                sent += 1
            else:
                errors += 1

        logger.info(f"Weekly reports job completed: {sent} sent, {errors} errors")
        return {"sent": sent, "errors": errors}

    except Exception as e:
        logger.error(f"Error in weekly reports job: {e}")
        return {"sent": 0, "errors": 1, "error": str(e)}


async def send_monthly_reports() -> dict:
    """Send monthly spending report to all active users. Runs 1st of month 9 AM IST."""
    from app.core.dependencies import get_whatsapp_service, get_user_service
    from app.modules.insights.reports import ReportsService

    whatsapp_service = get_whatsapp_service()
    user_service = get_user_service()
    reports_service = ReportsService()

    logger.info("Starting monthly reports job")

    try:
        users = await user_service.get_all_users()
        sent = 0
        errors = 0

        for user in users:
            if not user.phone_number:
                continue
            success = await reports_service.send_monthly_report(user, whatsapp_service)
            if success:
                sent += 1
            else:
                errors += 1

        logger.info(f"Monthly reports job completed: {sent} sent, {errors} errors")
        return {"sent": sent, "errors": errors}

    except Exception as e:
        logger.error(f"Error in monthly reports job: {e}")
        return {"sent": 0, "errors": 1, "error": str(e)}
