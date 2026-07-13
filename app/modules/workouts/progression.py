"""Progressive-overload engine (Phase 2).

Pure, DB-free logic. Given an exercise's recent session history (newest first),
produce an evidence-based double-progression suggestion for the next session.

Rules, in short:
- Track the best *working* set of the most recent session by estimated 1RM
  (Epley), so a descending-weight day like 35x8 / 30x6 / 25x9 is judged on its
  strongest effort, not the last set typed.
- Double progression: keep adding reps within a target range at a fixed weight;
  once you hit the top of the range, add the smallest sensible load and reset to
  the bottom of the range.
- Detect stalls (no e1RM improvement across the last 3 sessions) and recommend a
  ~10% deload instead of grinding.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

from app.modules.workouts.dto import ExerciseProgression, SetPerformance

# Big barbell compounds get a slightly lower, strength-leaning rep range.
_BIG_COMPOUND_KEYWORDS = (
    "squat",
    "deadlift",
    "bench",
    "overhead press",
    "ohp",
    "barbell row",
    "hip thrust",
)
# Lifts that jump in bigger absolute steps.
_LARGE_STEP_KEYWORDS = ("deadlift",)

_DEFAULT_RANGE: Tuple[int, int] = (8, 12)
_COMPOUND_RANGE: Tuple[int, int] = (6, 10)
_DEFAULT_INCREMENT = 2.5
_LARGE_INCREMENT = 5.0
_STALL_WINDOW = 3


@dataclass
class SetInput:
    weight_kg: Optional[float] = None
    reps: Optional[int] = None
    duration_seconds: Optional[int] = None


@dataclass
class SessionInput:
    performed_at: datetime
    sets: List[SetInput] = field(default_factory=list)


def estimate_1rm(weight_kg: Optional[float], reps: Optional[int]) -> Optional[float]:
    """Epley estimated 1RM. Returns None if inputs are unusable."""
    if not weight_kg or not reps or reps <= 0:
        return None
    return weight_kg * (1 + reps / 30.0)


def target_range(exercise_name: str) -> Tuple[int, int]:
    key = (exercise_name or "").lower()
    if any(k in key for k in _BIG_COMPOUND_KEYWORDS):
        return _COMPOUND_RANGE
    return _DEFAULT_RANGE


def weight_increment(exercise_name: str) -> float:
    key = (exercise_name or "").lower()
    if any(k in key for k in _LARGE_STEP_KEYWORDS):
        return _LARGE_INCREMENT
    return _DEFAULT_INCREMENT


def _round_to_plate(value: float) -> float:
    """Round to the nearest 0.5 kg (microplate-friendly)."""
    return round(value * 2) / 2


def _fmt(value: float) -> str:
    return f"{value:g}"


def _loaded_sets(sets: List[SetInput]) -> List[SetInput]:
    return [s for s in sets if s.weight_kg is not None and s.reps]


def pick_top_set(sets: List[SetInput]) -> Optional[SetInput]:
    """Best weighted set by estimated 1RM (ties broken by heavier weight)."""
    loaded = _loaded_sets(sets)
    if not loaded:
        return None
    return max(
        loaded,
        key=lambda s: (estimate_1rm(s.weight_kg, s.reps) or 0.0, s.weight_kg or 0.0),
    )


def _session_top_e1rm(session: SessionInput) -> Optional[float]:
    top = pick_top_set(session.sets)
    return estimate_1rm(top.weight_kg, top.reps) if top else None


def detect_stall(sessions: List[SessionInput]) -> bool:
    """Stalled if the newest session's top e1RM hasn't beaten the prior two."""
    e1rms = [_session_top_e1rm(s) for s in sessions[:_STALL_WINDOW]]
    if len(e1rms) < _STALL_WINDOW or any(v is None for v in e1rms):
        return False
    newest, *older = e1rms
    return all(newest <= v for v in older)


def _timed_or_bodyweight(
    name: str, last: SessionInput, sessions_analyzed: int
) -> ExerciseProgression:
    """Fallback progression for sets with no weight (bodyweight reps / timed holds)."""
    rep_only = [s for s in last.sets if s.reps]
    if rep_only:
        best = max(rep_only, key=lambda s: s.reps or 0)
        target = (best.reps or 0) + 2
        return ExerciseProgression(
            name=name,
            last_performed_at=last.performed_at,
            last_top_set=SetPerformance(reps=best.reps),
            recommended_reps=target,
            recommended_note="add reps",
            rationale=(
                f"Bodyweight movement — last best {best.reps} reps. "
                f"Aim for {target}, then add external load."
            ),
            sessions_analyzed=sessions_analyzed,
        )

    timed = [s for s in last.sets if s.duration_seconds]
    if timed:
        best = max(timed, key=lambda s: s.duration_seconds or 0)
        target = (best.duration_seconds or 0) + 10
        return ExerciseProgression(
            name=name,
            last_performed_at=last.performed_at,
            last_top_set=SetPerformance(duration_seconds=best.duration_seconds),
            recommended_duration_seconds=target,
            recommended_note="add time",
            rationale=f"Timed hold — last {best.duration_seconds}s. Aim for ~{target}s.",
            sessions_analyzed=sessions_analyzed,
        )

    return ExerciseProgression(
        name=name,
        last_performed_at=last.performed_at,
        recommended_note="log detail",
        rationale="No weight/rep data on the last session to progress from.",
        sessions_analyzed=sessions_analyzed,
    )


def analyze_exercise(name: str, sessions: List[SessionInput]) -> ExerciseProgression:
    """Produce a next-session suggestion for one exercise (sessions newest-first)."""
    if not sessions:
        return ExerciseProgression(
            name=name,
            recommended_note="no history",
            rationale="Log this exercise at least once to get a suggestion.",
            sessions_analyzed=0,
        )

    last = sessions[0]
    analyzed = len(sessions)
    top = pick_top_set(last.sets)
    if top is None:
        return _timed_or_bodyweight(name, last, analyzed)

    low, high = target_range(name)
    inc = weight_increment(name)
    e1rm = estimate_1rm(top.weight_kg, top.reps)
    last_top = SetPerformance(
        weight_kg=top.weight_kg,
        reps=top.reps,
        est_1rm=round(e1rm, 1) if e1rm else None,
    )

    if detect_stall(sessions):
        deload = _round_to_plate((top.weight_kg or 0) * 0.9)
        return ExerciseProgression(
            name=name,
            last_performed_at=last.performed_at,
            last_top_set=last_top,
            recommended_weight_kg=deload,
            recommended_reps=high,
            recommended_note="deload",
            rationale=(
                f"Top set stuck around {_fmt(top.weight_kg)}kg×{top.reps} across your "
                f"last {_STALL_WINDOW} sessions. Deload to ~{_fmt(deload)}kg, rebuild to "
                f"{high} reps, then push past the old best."
            ),
            stalled=True,
            sessions_analyzed=analyzed,
        )

    if top.reps >= high:
        new_w = _round_to_plate((top.weight_kg or 0) + inc)
        return ExerciseProgression(
            name=name,
            last_performed_at=last.performed_at,
            last_top_set=last_top,
            recommended_weight_kg=new_w,
            recommended_reps=low,
            recommended_note="add weight",
            rationale=(
                f"Hit {top.reps} reps at {_fmt(top.weight_kg)}kg (top of {low}-{high}). "
                f"Add {_fmt(inc)}kg → {_fmt(new_w)}kg and restart at {low} reps."
            ),
            sessions_analyzed=analyzed,
        )

    if top.reps >= low:
        return ExerciseProgression(
            name=name,
            last_performed_at=last.performed_at,
            last_top_set=last_top,
            recommended_weight_kg=top.weight_kg,
            recommended_reps=top.reps + 1,
            recommended_note="add a rep",
            rationale=(
                f"{_fmt(top.weight_kg)}kg for {top.reps} reps last time. Keep the weight "
                f"and aim for {top.reps + 1} — build to {high} before adding load."
            ),
            sessions_analyzed=analyzed,
        )

    return ExerciseProgression(
        name=name,
        last_performed_at=last.performed_at,
        last_top_set=last_top,
        recommended_weight_kg=top.weight_kg,
        recommended_reps=low,
        recommended_note="build reps",
        rationale=(
            f"{_fmt(top.weight_kg)}kg for {top.reps} reps is below the {low}-{high} "
            f"target. Hold the weight and build to {low}+ reps before adding load."
        ),
        sessions_analyzed=analyzed,
    )
