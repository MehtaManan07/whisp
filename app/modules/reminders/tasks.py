# app/modules/reminders/tasks.py

import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.celery_worker import celery_app
from app.core.db.engine import get_db_util
from app.core.dependencies import (
    get_category_classifier,
    get_intent_classifier,
    get_llm_service,
    get_user_service,
)
from app.modules.reminders.service import ReminderService
from app.integrations.whatsapp.service import WhatsAppService
from app.core.orchestrator import MessageOrchestrator

logger = logging.getLogger(__name__)


@celery_app.task(name="check_due_reminders")
def check_due_reminders():
    """Simple task that runs every 2 minutes to check and send due reminders."""
    logger.info("🔄 Starting scheduled reminder check task...")
    try:
        asyncio.run(_process_due_reminders())
        logger.info("✅ Reminder check task completed successfully")
    except Exception as e:
        logger.error(f"❌ Reminder check task failed: {e}")
        raise


async def _process_due_reminders():
    """Check for due reminders and send WhatsApp notifications."""
    logger.info("🔍 Checking for due reminders...")
    try:
        async for db in get_db_util():
            service = ReminderService()
            due_reminders = await service.get_due_reminders(db, limit=50)

            if not due_reminders:
                logger.info("📭 No due reminders found")
                return

            logger.info(f"📬 Found {len(due_reminders)} due reminders")

            # Send notifications
            users_service = get_user_service()
            intent_classifier = get_intent_classifier()
            llm_service = get_llm_service()
            category_classifier = get_category_classifier()
            orchestrator = MessageOrchestrator(
                users_service, intent_classifier, llm_service, category_classifier
            )
            whatsapp_service = WhatsAppService(orchestrator)

            print(due_reminders)

            for reminder in due_reminders:
                try:
                    # Get user phone (assuming you have this field)
                    user = reminder.user
                    if not user or not user.phone:
                        continue

                    # Send notification
                    message = f"🔔 Reminder: {reminder.title}"
                    if reminder.amount:
                        message += f"\nAmount: ₹{reminder.amount}"

                    await whatsapp_service.send_text(user.phone, message)

                    # Mark as processed
                    await service.process_triggered_reminder(db, reminder)

                except Exception as e:
                    logger.error(f"Failed to process reminder {reminder.id}: {e}")

    except Exception as e:
        logger.error(f"Error checking due reminders: {e}")
