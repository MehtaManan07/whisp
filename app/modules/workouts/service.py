import logging
from typing import List, Optional

import dateparser
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.db.engine import run_db
from app.core.exceptions import DatabaseError
from app.modules.workouts.dto import (
    LogWorkoutModel,
    ViewWorkoutsModel,
    WorkoutExerciseResponse,
    WorkoutResponse,
    WorkoutSetResponse,
)
from app.modules.workouts.models import Workout, WorkoutExercise, WorkoutSet
from app.utils.datetime import to_utc, utc_now

logger = logging.getLogger(__name__)

DEFAULT_WORKOUT_LIMIT = 5


def normalize_exercise_name(name: str) -> str:
    """Normalize an exercise name for cross-session grouping.

    Lowercases, collapses whitespace. Keeps equipment qualifier so that
    'Squat (Barbell)' and 'Squat (Smith)' remain distinct progressions.
    """
    return " ".join((name or "").lower().split())


def _to_response(workout: Workout) -> WorkoutResponse:
    """Build a detached response DTO while the session is still open."""
    return WorkoutResponse(
        id=workout.id,
        name=workout.name,
        performed_at=workout.performed_at,
        duration_seconds=workout.duration_seconds,
        source=workout.source,
        notes=workout.notes,
        exercises=[
            WorkoutExerciseResponse(
                name=ex.name,
                is_warmup=ex.is_warmup,
                sets=[
                    WorkoutSetResponse(
                        set_index=s.set_index,
                        weight_kg=s.weight_kg,
                        reps=s.reps,
                        duration_seconds=s.duration_seconds,
                        rir=s.rir,
                    )
                    for s in ex.sets
                ],
            )
            for ex in workout.exercises
        ],
    )


class WorkoutsService:
    def __init__(self):
        self.logger = logger

    async def create_workout(
        self, data: LogWorkoutModel, user_timezone: str = "UTC"
    ) -> WorkoutResponse:
        """Persist a workout with its exercises and sets."""

        def _create(db: Session) -> WorkoutResponse:
            try:
                performed_at = data.performed_at
                if performed_at and performed_at.tzinfo is None:
                    performed_at = to_utc(performed_at, user_timezone)
                elif performed_at is None:
                    performed_at = utc_now()

                workout = Workout(
                    user_id=data.user_id,
                    name=data.name,
                    performed_at=performed_at,
                    source=data.source or "telegram",
                    notes=data.notes,
                    created_at=utc_now(),
                )

                for order_index, exercise in enumerate(data.exercises):
                    ex_row = WorkoutExercise(
                        name=exercise.name,
                        normalized_key=normalize_exercise_name(exercise.name),
                        order_index=order_index,
                        is_warmup=exercise.is_warmup,
                        created_at=utc_now(),
                    )
                    for set_index, s in enumerate(exercise.sets):
                        ex_row.sets.append(
                            WorkoutSet(
                                set_index=set_index,
                                weight_kg=s.weight_kg,
                                reps=s.reps,
                                duration_seconds=s.duration_seconds,
                                rir=s.rir,
                                created_at=utc_now(),
                            )
                        )
                    workout.exercises.append(ex_row)

                db.add(workout)
                db.commit()
                db.refresh(workout)

                logger.info(
                    "Workout created: user_id=%s name=%s exercises=%s",
                    data.user_id,
                    data.name,
                    len(data.exercises),
                )
                return _to_response(workout)
            except Exception as e:
                db.rollback()
                logger.error(f"Database error during workout creation: {str(e)}")
                raise DatabaseError(f"create workout: {str(e)}")

        return await run_db(_create)

    async def get_workouts(
        self, data: ViewWorkoutsModel, user_timezone: str = "UTC"
    ) -> List[WorkoutResponse]:
        """Fetch recent workouts with optional name/exercise/date filters."""

        def _get(db: Session) -> List[WorkoutResponse]:
            start_date = None
            end_date = None

            if data.start_date:
                parsed = dateparser.parse(
                    data.start_date,
                    settings={"TIMEZONE": user_timezone, "RETURN_AS_TIMEZONE_AWARE": True},
                )
                if parsed:
                    start_date = parsed.astimezone(utc_now().tzinfo)

            if data.end_date:
                parsed = dateparser.parse(
                    data.end_date,
                    settings={"TIMEZONE": user_timezone, "RETURN_AS_TIMEZONE_AWARE": True},
                )
                if parsed:
                    end_date = parsed.astimezone(utc_now().tzinfo)

            query = (
                select(Workout)
                .where(Workout.user_id == data.user_id, Workout.deleted_at.is_(None))
                .options(selectinload(Workout.exercises).selectinload(WorkoutExercise.sets))
            )

            if data.name:
                query = query.where(Workout.name.ilike(f"%{data.name}%"))
            if start_date:
                query = query.where(Workout.performed_at >= start_date)
            if end_date:
                query = query.where(Workout.performed_at <= end_date)
            if data.exercise_name:
                key = f"%{normalize_exercise_name(data.exercise_name)}%"
                query = query.where(
                    Workout.exercises.any(WorkoutExercise.normalized_key.ilike(key))
                )

            limit = data.limit or DEFAULT_WORKOUT_LIMIT
            query = query.order_by(Workout.performed_at.desc()).limit(limit)

            workouts = db.execute(query).scalars().all()
            return [_to_response(w) for w in workouts]

        return await run_db(_get)

    async def get_latest_workout(
        self, user_id: int
    ) -> Optional[WorkoutResponse]:
        """Most recent workout for a user, or None."""

        def _get(db: Session) -> Optional[WorkoutResponse]:
            workout = db.execute(
                select(Workout)
                .where(Workout.user_id == user_id, Workout.deleted_at.is_(None))
                .options(selectinload(Workout.exercises).selectinload(WorkoutExercise.sets))
                .order_by(Workout.performed_at.desc())
                .limit(1)
            ).scalar_one_or_none()
            return _to_response(workout) if workout else None

        return await run_db(_get)
