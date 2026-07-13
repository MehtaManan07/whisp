from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Input DTOs (LLM-extracted)
# ---------------------------------------------------------------------------
class WorkoutSetModel(BaseModel):
    """A single set within an exercise."""

    weight_kg: Optional[float] = Field(
        None, description="Weight lifted in kilograms for this set"
    )
    reps: Optional[int] = Field(None, description="Number of repetitions performed")
    duration_seconds: Optional[int] = Field(
        None, description="Duration in seconds for timed sets (warm-ups, planks, cardio)"
    )
    rir: Optional[int] = Field(
        None, description="Reps in reserve, if explicitly reported"
    )


class WorkoutExerciseModel(BaseModel):
    """An exercise performed within the workout, with its sets."""

    name: str = Field(..., description="Exercise name, e.g. 'Squat (Barbell)'")
    is_warmup: bool = Field(
        False, description="True if this is a warm-up entry rather than a working exercise"
    )
    sets: List[WorkoutSetModel] = Field(
        default_factory=list, description="Ordered list of sets for this exercise"
    )


class LogWorkoutModel(BaseModel):
    """DTO for logging a completed workout session."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user_id": 1,
                    "name": "Legs",
                    "source": "hevy",
                    "exercises": [
                        {
                            "name": "Warm Up",
                            "is_warmup": True,
                            "sets": [{"duration_seconds": 343}],
                        },
                        {
                            "name": "Squat (Barbell)",
                            "is_warmup": False,
                            "sets": [
                                {"weight_kg": 35, "reps": 8},
                                {"weight_kg": 30, "reps": 6},
                                {"weight_kg": 25, "reps": 9},
                            ],
                        },
                        {
                            "name": "Standing Calf Raise (Smith)",
                            "is_warmup": False,
                            "sets": [
                                {"weight_kg": 40, "reps": 10},
                                {"weight_kg": 40, "reps": 10},
                            ],
                        },
                    ],
                }
            ]
        }
    )

    user_id: int = Field(..., description="ID of the user who performed the workout")
    name: Optional[str] = Field(
        None, description="Name/title of the workout, e.g. 'Legs', 'Upper A'"
    )
    performed_at: Optional[datetime] = Field(
        None, description="When the workout was performed (ISO 8601). Omit if not stated."
    )
    source: Optional[str] = Field(
        None, description="Origin of the log, e.g. 'hevy', 'telegram', 'manual'"
    )
    notes: Optional[str] = Field(None, description="Any free-form notes about the session")
    exercises: List[WorkoutExerciseModel] = Field(
        default_factory=list, description="Ordered list of exercises performed"
    )


class ViewWorkoutsModel(BaseModel):
    """DTO for querying past workouts."""

    user_id: int = Field(..., description="ID of the user")
    name: Optional[str] = Field(
        None, description="Filter by workout name (partial match), e.g. 'legs'"
    )
    exercise_name: Optional[str] = Field(
        None, description="Filter to sessions containing this exercise (partial match)"
    )
    start_date: Optional[str] = Field(
        None, description="Only workouts on/after this date (ISO format)"
    )
    end_date: Optional[str] = Field(
        None, description="Only workouts on/before this date (ISO format)"
    )
    limit: Optional[int] = Field(
        None, description="Maximum number of workouts to return (default 5)"
    )


class NextWorkoutModel(BaseModel):
    """DTO for requesting a progression suggestion for the next session."""

    user_id: int = Field(..., description="ID of the user")
    name: Optional[str] = Field(
        None,
        description="Workout day to plan (partial match), e.g. 'legs', 'upper a'. "
        "Omit to use the most recent session as the template.",
    )
    exercise_name: Optional[str] = Field(
        None,
        description="Set only if the user asks about ONE specific lift, e.g. 'squat'. "
        "Overrides `name` and returns a single-exercise suggestion.",
    )


# ---------------------------------------------------------------------------
# Response DTOs (built inside the DB session, safe to render after close)
# ---------------------------------------------------------------------------
class WorkoutSetResponse(BaseModel):
    set_index: int
    weight_kg: Optional[float] = None
    reps: Optional[int] = None
    duration_seconds: Optional[int] = None
    rir: Optional[int] = None


class WorkoutExerciseResponse(BaseModel):
    name: str
    is_warmup: bool = False
    sets: List[WorkoutSetResponse] = Field(default_factory=list)


class WorkoutResponse(BaseModel):
    id: int
    name: Optional[str] = None
    performed_at: datetime
    duration_seconds: Optional[int] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    exercises: List[WorkoutExerciseResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Progression / coaching DTOs (Phase 2)
# ---------------------------------------------------------------------------
class SetPerformance(BaseModel):
    """A single reference set used in a progression suggestion."""

    weight_kg: Optional[float] = None
    reps: Optional[int] = None
    duration_seconds: Optional[int] = None
    est_1rm: Optional[float] = None


class ExerciseProgression(BaseModel):
    """Progression suggestion for one exercise."""

    name: str
    last_performed_at: Optional[datetime] = None
    last_top_set: Optional[SetPerformance] = None
    recommended_weight_kg: Optional[float] = None
    recommended_reps: Optional[int] = None
    recommended_duration_seconds: Optional[int] = None
    # Short action label: 'add weight', 'add a rep', 'build reps', 'deload', etc.
    recommended_note: str = ""
    rationale: str = ""
    stalled: bool = False
    sessions_analyzed: int = 0


class NextWorkoutResponse(BaseModel):
    """A full next-session plan: one progression per exercise."""

    workout_name: Optional[str] = None
    based_on_date: Optional[datetime] = None
    exercises: List[ExerciseProgression] = Field(default_factory=list)
    # Set when there's nothing to suggest (no history / no match).
    message: Optional[str] = None
