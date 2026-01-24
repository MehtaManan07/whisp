"""
Background jobs for the scheduler.
These functions run outside of request context and manage their own DB sessions.
"""

import logging
from sqlalchemy import and_, select

from app.core.db.engine import AsyncSessionLocal
from app.modules.reminders.models import Reminder
from app.utils.datetime import utc_now

logger = logging.getLogger(__name__)


async def process_due_reminders() -> dict:
    """
    Process all due reminders.
    
    This job runs periodically to check for reminders that are due
    and sends WhatsApp notifications for each one.
    
    Returns:
        Summary of processed reminders
    """
    # Import here to avoid circular imports
    from app.core.dependencies import (
        get_user_service,
        get_whatsapp_service,
        get_reminder_service,
    )
    
    user_service = get_user_service()
    whatsapp_service = get_whatsapp_service()
    reminder_service = get_reminder_service()
    
    processed_count = 0
    error_count = 0
    
    logger.info("Starting due reminders processing job")
    
    async with AsyncSessionLocal() as db:
        try:
            # Get all due reminders
            result = await db.execute(
                select(Reminder).where(
                    and_(
                        Reminder.is_active == True,
                        Reminder.next_trigger_at <= utc_now(),
                        Reminder.deleted_at.is_(None),
                    )
                )
            )
            due_reminders = list(result.scalars().all())
            
            if not due_reminders:
                logger.debug("No due reminders found")
                return {"processed": 0, "errors": 0}
            
            logger.info(f"Found {len(due_reminders)} due reminders")
            
            for reminder in due_reminders:
                try:
                    result = await reminder_service.process_single_reminder(
                        db=db,
                        reminder_id=reminder.id,
                        user_service=user_service,
                        whatsapp_service=whatsapp_service,
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


async def process_kraftculture_emails() -> dict:
    """
    Process Kraftculture order emails.
    
    This job runs periodically to fetch new order emails from Gmail,
    parse them, store in database, and send WhatsApp notifications.
    
    Returns:
        Summary of processed emails
    """
    # Import here to avoid circular imports
    from app.core.dependencies import get_kraftculture_service
    
    kraftculture_service = get_kraftculture_service()
    
    logger.info("Starting Kraftculture email processing job")
    
    async with AsyncSessionLocal() as db:
        try:
            result = await kraftculture_service.process_emails(db=db)
            
            logger.info(
                f"Kraftculture job completed: {result.processed_count} processed, "
                f"{result.sent_count} sent, {len(result.errors)} errors"
            )
            
            return {
                "processed": result.processed_count,
                "sent": result.sent_count,
                "errors": len(result.errors),
            }
            
        except Exception as e:
            logger.error(f"Error in Kraftculture job: {e}")
            return {"processed": 0, "sent": 0, "errors": 1, "error": str(e)}
