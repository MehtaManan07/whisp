import logging
from typing import List, Optional

import dateparser
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.db.engine import run_db
from app.core.exceptions import DatabaseError
from app.modules.workouts.dto import (
    LogWorkoutModel,
    NextWorkoutModel,
    NextWorkoutResponse,
    ViewWorkoutsModel,
    WorkoutExerciseResponse,
    WorkoutResponse,
    WorkoutSetResponse,
)
from app.modules.workouts.models import Workout, WorkoutExercise, WorkoutSet
from app.modules.workouts.progression import (
    SessionInput,
    SetInput,
    analyze_exercise,
)
from app.utils.datetime import to_utc, utc_now

logger = logging.getLogger(__name__)

DEFAULT_WORKOUT_LIMIT = 5
# How many past sessions of an exercise to feed the progression engine.
PROGRESSION_HISTORY_LIMIT = 6


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

    # ------------------------------------------------------------------
    # Phase 2 — progression / "what should I do next" coaching
    # ------------------------------------------------------------------
    def _load_exercise_sessions(
        self, db: Session, user_id: int, normalized_key: str, limit: int
    ) -> List[SessionInput]:
        """Recent working sessions of one exercise (newest first) for progression."""
        rows = db.execute(
            select(WorkoutExercise, Workout.performed_at)
            .join(Workout, WorkoutExercise.workout_id == Workout.id)
            .where(
                Workout.user_id == user_id,
                Workout.deleted_at.is_(None),
                WorkoutExercise.deleted_at.is_(None),
                WorkoutExercise.is_warmup.is_(False),
                WorkoutExercise.normalized_key == normalized_key,
            )
            .options(selectinload(WorkoutExercise.sets))
            .order_by(Workout.performed_at.desc())
            .limit(limit)
        ).all()

        sessions: List[SessionInput] = []
        for exercise, performed_at in rows:
            ordered = sorted(exercise.sets, key=lambda s: s.set_index)
            sessions.append(
                SessionInput(
                    performed_at=performed_at,
                    sets=[
                        SetInput(
                            weight_kg=s.weight_kg,
                            reps=s.reps,
                            duration_seconds=s.duration_seconds,
                        )
                        for s in ordered
                    ],
                )
            )
        return sessions

    def _resolve_exercise(
        self, db: Session, user_id: int, query: str
    ) -> Optional[tuple]:
        """Find the most recent exercise matching a loose name → (display_name, key)."""
        key_like = f"%{normalize_exercise_name(query)}%"
        row = db.execute(
            select(WorkoutExercise.name, WorkoutExercise.normalized_key)
            .join(Workout, WorkoutExercise.workout_id == Workout.id)
            .where(
                Workout.user_id == user_id,
                Workout.deleted_at.is_(None),
                WorkoutExercise.deleted_at.is_(None),
                WorkoutExercise.is_warmup.is_(False),
                WorkoutExercise.normalized_key.ilike(key_like),
            )
            .order_by(Workout.performed_at.desc())
            .limit(1)
        ).first()
        return (row.name, row.normalized_key) if row else None

    async def get_next_workout(
        self, data: NextWorkoutModel
    ) -> NextWorkoutResponse:
        """Build a progressive-overload plan for the next session."""

        def _get(db: Session) -> NextWorkoutResponse:
            workout_name: Optional[str] = None
            based_on = None

            # Single-lift mode ("how much should I squat next time").
            if data.exercise_name:
                resolved = self._resolve_exercise(db, data.user_id, data.exercise_name)
                if not resolved:
                    return NextWorkoutResponse(
                        message=(
                            f"I don't have any history for '{data.exercise_name}' yet. "
                            "Log a session with it and I'll suggest a progression."
                        )
                    )
                targets = [resolved]
            # Whole-session mode: use a named template or the latest workout.
            else:
                query = (
                    select(Workout)
                    .where(
                        Workout.user_id == data.user_id,
                        Workout.deleted_at.is_(None),
                    )
                    .options(
                        selectinload(Workout.exercises).selectinload(
                            WorkoutExercise.sets
                        )
                    )
                )
                if data.name:
                    query = query.where(Workout.name.ilike(f"%{data.name}%"))
                template = db.execute(
                    query.order_by(Workout.performed_at.desc()).limit(1)
                ).scalar_one_or_none()

                if not template:
                    return NextWorkoutResponse(
                        message=(
                            "I couldn't find a matching workout to plan from."
                            if data.name
                            else "No workouts logged yet — log one and I'll plan your next session."
                        )
                    )

                workout_name = template.name
                based_on = template.performed_at
                targets = [
                    (ex.name, ex.normalized_key)
                    for ex in template.exercises
                    if not ex.is_warmup
                ]
                if not targets:
                    return NextWorkoutResponse(
                        workout_name=workout_name,
                        based_on_date=based_on,
                        message="That session had no working exercises to progress.",
                    )

            progressions = []
            latest_seen = based_on
            for display_name, key in targets:
                sessions = self._load_exercise_sessions(
                    db, data.user_id, key, PROGRESSION_HISTORY_LIMIT
                )
                progressions.append(analyze_exercise(display_name, sessions))
                if sessions and (
                    latest_seen is None or sessions[0].performed_at > latest_seen
                ):
                    latest_seen = sessions[0].performed_at

            return NextWorkoutResponse(
                workout_name=workout_name,
                based_on_date=based_on or latest_seen,
                exercises=progressions,
            )

        return await run_db(_get)
