from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import BaseModel
from app.utils.datetime import utc_now

if TYPE_CHECKING:
    pass


class Workout(BaseModel):
    """A single training session (e.g. an 'Upper A' or 'Legs' day)."""

    __tablename__ = "workouts"
    __table_args__ = (
        Index("idx_workouts_performed_at", "performed_at"),
        Index("idx_workouts_user_performed", "user_id", "performed_at"),
        Index("idx_workouts_deleted_at", "deleted_at"),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )

    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Where the log came from: 'hevy', 'telegram', 'manual', etc.
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    source_message_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, index=True
    )

    exercises: Mapped[List["WorkoutExercise"]] = relationship(
        "WorkoutExercise",
        back_populates="workout",
        cascade="all, delete-orphan",
        order_by="WorkoutExercise.order_index",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Workout(name={self.name!r}, user_id={self.user_id})>"


class WorkoutExercise(BaseModel):
    """An exercise performed within a workout (e.g. 'Squat (Barbell)')."""

    __tablename__ = "workout_exercises"
    __table_args__ = (
        Index("idx_workout_exercises_workout", "workout_id"),
        Index("idx_workout_exercises_normalized", "normalized_key"),
    )

    workout_id: Mapped[int] = mapped_column(
        ForeignKey("workouts.id"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String, nullable=False)

    # Lowercased/normalized name used for grouping history across sessions
    # (progressive-overload lookups in later phases).
    normalized_key: Mapped[str] = mapped_column(String, nullable=False, index=True)

    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_warmup: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    workout: Mapped["Workout"] = relationship(
        "Workout", back_populates="exercises", lazy="noload"
    )

    sets: Mapped[List["WorkoutSet"]] = relationship(
        "WorkoutSet",
        back_populates="exercise",
        cascade="all, delete-orphan",
        order_by="WorkoutSet.set_index",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<WorkoutExercise(name={self.name!r}, sets={len(self.sets) if self.sets else 0})>"


class WorkoutSet(BaseModel):
    """A single set of an exercise (e.g. 35 kg x 8, or a 5min 43s warm-up)."""

    __tablename__ = "workout_sets"
    __table_args__ = (Index("idx_workout_sets_exercise", "exercise_id"),)

    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("workout_exercises.id"), nullable=False, index=True
    )

    set_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    reps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # For timed sets (warm-ups, planks, cardio).
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Reps in reserve, if the user reports it.
    rir: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    exercise: Mapped["WorkoutExercise"] = relationship(
        "WorkoutExercise", back_populates="sets", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<WorkoutSet(weight_kg={self.weight_kg}, reps={self.reps})>"
