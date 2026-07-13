from app.intelligence.intent.base_handler import BaseHandlers
from app.intelligence.intent.decorators import intent_handler
from app.intelligence.intent.types import CLASSIFIED_RESULT, IntentType
from app.modules.workouts.dto import (
    LogWorkoutModel,
    NextWorkoutModel,
    ViewWorkoutsModel,
)
from app.modules.workouts.formatter import (
    format_log_confirmation,
    format_next_workout,
    format_workout_list,
)
from app.modules.workouts.service import WorkoutsService


class WorkoutHandlers(BaseHandlers):
    def __init__(self):
        super().__init__()
        self.service = WorkoutsService()

    @intent_handler(IntentType.LOG_WORKOUT)
    async def log_workout(
        self, classified_result: CLASSIFIED_RESULT, user_id: int, user_timezone: str = "UTC"
    ) -> str:
        """Handle logging a completed workout session."""
        dto_instance, _ = classified_result
        if not dto_instance:
            return (
                "I couldn't read that workout. Try pasting your Hevy session, or "
                "text me something like 'did legs — squat 35x8, 35x8, 35x9; leg curl 45x12, 45x11'."
            )
        if not isinstance(dto_instance, LogWorkoutModel):
            return "Invalid data for logging a workout."
        if not dto_instance.user_id:
            dto_instance.user_id = user_id

        if not dto_instance.exercises:
            return (
                "I got the workout but couldn't find any exercises/sets. "
                "Include them like 'squat 35kg x 8, 35kg x 8'."
            )

        saved = await self.service.create_workout(
            data=dto_instance, user_timezone=user_timezone
        )
        return format_log_confirmation(saved.name, saved.exercises)

    @intent_handler(IntentType.VIEW_WORKOUTS)
    async def view_workouts(
        self, classified_result: CLASSIFIED_RESULT, user_id: int, user_timezone: str = "UTC"
    ) -> str:
        """Handle viewing past workouts."""
        dto_instance, _ = classified_result
        if not isinstance(dto_instance, ViewWorkoutsModel):
            # Fall back to a sensible default query if extraction produced nothing usable.
            dto_instance = ViewWorkoutsModel(user_id=user_id)
        if not dto_instance.user_id:
            dto_instance.user_id = user_id

        workouts = await self.service.get_workouts(
            data=dto_instance, user_timezone=user_timezone
        )
        return format_workout_list(workouts, user_timezone)

    @intent_handler(IntentType.NEXT_WORKOUT)
    async def next_workout(
        self, classified_result: CLASSIFIED_RESULT, user_id: int, user_timezone: str = "UTC"
    ) -> str:
        """Suggest progressive-overload targets for the next session."""
        dto_instance, _ = classified_result
        if not isinstance(dto_instance, NextWorkoutModel):
            # No usable extraction → plan from the most recent session.
            dto_instance = NextWorkoutModel(user_id=user_id)
        if not dto_instance.user_id:
            dto_instance.user_id = user_id

        plan = await self.service.get_next_workout(dto_instance)
        return format_next_workout(plan, user_timezone)
