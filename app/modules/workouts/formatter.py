"""Human-readable rendering for workouts (Telegram-friendly plain text)."""

from typing import List

from app.modules.workouts.dto import (
    ExerciseProgression,
    NextWorkoutResponse,
    WorkoutExerciseResponse,
    WorkoutResponse,
)
from app.utils.datetime import format_datetime_for_user


def format_duration(seconds: int) -> str:
    """Render seconds as a compact '5min 43s' / '1h 2min' style string."""
    if seconds is None:
        return ""
    seconds = int(seconds)
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    parts: List[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}min")
    if secs and not hours:
        parts.append(f"{secs}s")
    return " ".join(parts) if parts else f"{secs}s"


def format_set(s) -> str:
    """Render a single set: '35 kg x 8' or timed '5min 43s'."""
    if s.weight_kg is not None and s.reps is not None:
        weight = f"{s.weight_kg:g} kg"
        text = f"{weight} x {s.reps}"
    elif s.reps is not None:
        text = f"{s.reps} reps"
    elif s.duration_seconds is not None:
        text = format_duration(s.duration_seconds)
    elif s.weight_kg is not None:
        text = f"{s.weight_kg:g} kg"
    else:
        text = "—"
    if s.rir is not None:
        text += f" @ {s.rir} RIR"
    return text


def _count_working_sets(exercises: List[WorkoutExerciseResponse]) -> int:
    return sum(len(ex.sets) for ex in exercises if not ex.is_warmup)


def format_workout_detail(workout: WorkoutResponse, user_timezone: str = "UTC") -> str:
    """Full, exercise-by-exercise rendering of one workout."""
    lines: List[str] = []

    title = workout.name or "Workout"
    date_str = format_datetime_for_user(
        workout.performed_at, user_timezone, "%b %d, %Y"
    )
    header = f"🏋️ *{title}* — {date_str}"
    lines.append(header)

    meta_bits = []
    if workout.duration_seconds:
        meta_bits.append(f"⏱ {format_duration(workout.duration_seconds)}")
    working = _count_working_sets(workout.exercises)
    if working:
        meta_bits.append(f"{working} working sets")
    if workout.source:
        meta_bits.append(f"via {workout.source}")
    if meta_bits:
        lines.append(" · ".join(meta_bits))

    lines.append("")

    for ex in workout.exercises:
        label = f"*{ex.name}*"
        if ex.is_warmup:
            label += " (warm-up)"
        lines.append(label)
        for s in ex.sets:
            lines.append(f"  • {format_set(s)}")

    if workout.notes:
        lines.append("")
        lines.append(f"📝 {workout.notes}")

    return "\n".join(lines)


def format_workout_list(
    workouts: List[WorkoutResponse], user_timezone: str = "UTC"
) -> str:
    """Compact summary of multiple workouts."""
    if not workouts:
        return (
            "🏋️ No workouts found yet. Log one by pasting your Hevy session or "
            "texting me something like 'did legs, squat 35x8, 35x8, 35x9'."
        )

    if len(workouts) == 1:
        return format_workout_detail(workouts[0], user_timezone)

    lines: List[str] = [f"🏋️ Your last {len(workouts)} workouts:", ""]
    for w in workouts:
        date_str = format_datetime_for_user(w.performed_at, user_timezone, "%b %d")
        working = _count_working_sets(w.exercises)
        ex_count = len([e for e in w.exercises if not e.is_warmup])
        title = w.name or "Workout"
        lines.append(
            f"• *{title}* — {date_str} ({ex_count} exercises, {working} sets)"
        )
    lines.append("")
    lines.append("Reply with a workout name (e.g. 'show my last legs') for full details.")
    return "\n".join(lines)


def format_log_confirmation(
    workout_name: str, exercises: List[WorkoutExerciseResponse]
) -> str:
    """Confirmation shown right after a workout is logged."""
    working_ex = [e for e in exercises if not e.is_warmup]
    total_sets = _count_working_sets(exercises)

    lines = [
        f"✅ Logged *{workout_name or 'workout'}* — "
        f"{len(working_ex)} exercises, {total_sets} working sets.",
        "",
    ]
    for ex in working_ex:
        if not ex.sets:
            continue
        sets_str = ", ".join(format_set(s) for s in ex.sets)
        lines.append(f"• {ex.name}: {sets_str}")

    return "\n".join(lines)


def _format_target(ex: ExerciseProgression) -> str:
    """The headline prescription for one exercise, e.g. '37.5 kg × 8'."""
    if ex.recommended_weight_kg is not None and ex.recommended_reps is not None:
        return f"{ex.recommended_weight_kg:g} kg × {ex.recommended_reps}"
    if ex.recommended_reps is not None:
        return f"{ex.recommended_reps} reps"
    if ex.recommended_duration_seconds is not None:
        return format_duration(ex.recommended_duration_seconds)
    return ex.recommended_note or "—"


def format_next_workout(
    plan: NextWorkoutResponse, user_timezone: str = "UTC"
) -> str:
    """Render a progressive-overload plan for the next session."""
    if not plan.exercises:
        return f"🎯 {plan.message or 'Nothing to plan yet — log a workout first.'}"

    title = plan.workout_name or "session"
    header = f"🎯 *Next {title}*"
    if plan.based_on_date:
        date_str = format_datetime_for_user(plan.based_on_date, user_timezone, "%b %d")
        header += f" — based on {date_str}"

    lines: List[str] = [header, "_Progressive-overload targets from your history:_", ""]

    for ex in plan.exercises:
        marker = "⚠️ " if ex.stalled else ""
        lines.append(f"{marker}*{ex.name}* → {_format_target(ex)}")
        if ex.rationale:
            lines.append(f"  ↳ {ex.rationale}")

    lines.append("")
    lines.append("Leave 1–3 reps in reserve. Log it after and I'll re-calc next time.")
    return "\n".join(lines)
