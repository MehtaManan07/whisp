from sqlalchemy.ext.asyncio import AsyncSession
from app.intelligence.intent.base_handler import BaseHandlers
from app.intelligence.intent.decorators import intent_handler
from app.intelligence.intent.types import CLASSIFIED_RESULT, IntentType
from app.modules.reminders.dto import CreateReminderDTO, ListRemindersDTO
from app.modules.reminders.service import ReminderService


class ReminderHandlers(BaseHandlers):
    def __init__(self):
        super().__init__()
        self.service = ReminderService()

    @intent_handler(IntentType.SET_REMINDER)
    async def set_reminder(
        self, classified_result: CLASSIFIED_RESULT, user_id: int, db: AsyncSession
    ) -> str:
        """Handle set reminder intent."""
        dto_instance, intent = classified_result
        if not dto_instance:
            return "I couldn't understand the reminder details. Please provide the reminder details."
        if not isinstance(dto_instance, CreateReminderDTO):
            return "Invalid data for creating reminder."

        await self.service.create_reminder(db=db, user_id=user_id, data=dto_instance)

        return "Reminder set successfully!"

    @intent_handler(IntentType.VIEW_REMINDERS)
    async def view_reminders(
        self, classified_result: CLASSIFIED_RESULT, user_id: int, db: AsyncSession
    ) -> str:
        """Handle view reminders intent."""
        dto_instance, intent = classified_result
        if not dto_instance:
            return "I couldn't understand the reminder details. Please provide the reminder details."
        if not isinstance(dto_instance, ListRemindersDTO):
            return "Invalid data for viewing reminders."

        list_dto = ListRemindersDTO(
            user_id=dto_instance.user_id, reminder_type=None, is_active=True
        )
        reminders = await self.service.list_reminders(db=db, data=list_dto)

        # Handle case where no reminders found
        if not reminders:
            return "📋 No active reminders found. Set one with 'remind me to [task]' or create a bill reminder!"

        # Format the response
        reminder_count = len(reminders)
        response_parts = [f"📋 Your Active Reminders ({reminder_count}):", ""]

        # Add each reminder as a numbered item
        for idx, reminder in enumerate(reminders, 1):
            response_parts.append(f"{idx}. {reminder.to_human_message()}")
            response_parts.append("")  # Add spacing between reminders

        return "\n".join(response_parts)
