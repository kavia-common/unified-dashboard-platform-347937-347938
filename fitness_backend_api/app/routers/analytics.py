from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.deps import get_db
from app.models.fitness import ActivityLog, BodyMetric, WorkoutLog
from app.models.user import AppUser

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get(
    "/summary",
    summary="Analytics summary",
    description="Returns summary stats for the current user over a time window.",
    operation_id="analytics_summary",
)
def analytics_summary(
    days: int = Query(28, ge=1, le=365, description="Lookback window in days."),
    user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Provide dashboard-friendly summary counts/aggregates."""
    since = datetime.utcnow() - timedelta(days=days)

    workouts_count = db.execute(
        select(func.count())
        .select_from(WorkoutLog)
        .where(WorkoutLog.user_id == user.id)
        .where(WorkoutLog.started_at >= since)
        .where(WorkoutLog.deleted_at.is_(None))
    ).scalar_one()

    steps_sum = db.execute(
        select(func.coalesce(func.sum(ActivityLog.steps), 0))
        .select_from(ActivityLog)
        .where(ActivityLog.user_id == user.id)
        .where(ActivityLog.occurred_on >= date.today() - timedelta(days=days))
        .where(ActivityLog.deleted_at.is_(None))
    ).scalar_one()

    latest_weight = db.execute(
        select(BodyMetric.weight_kg)
        .where(BodyMetric.user_id == user.id)
        .where(BodyMetric.deleted_at.is_(None))
        .order_by(BodyMetric.measured_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    return {
        "window_days": days,
        "workouts_count": int(workouts_count or 0),
        "steps_sum": int(steps_sum or 0),
        "latest_weight_kg": float(latest_weight) if latest_weight is not None else None,
    }


@router.get(
    "/timeseries/steps",
    summary="Steps time-series",
    description="Returns daily steps totals for the current user over a time window.",
    operation_id="analytics_steps_timeseries",
)
def analytics_steps_timeseries(
    days: int = Query(28, ge=1, le=365, description="Lookback window in days."),
    user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return daily steps sums as [{date, steps}]."""
    start_day = date.today() - timedelta(days=days - 1)

    rows = db.execute(
        select(ActivityLog.occurred_on, func.coalesce(func.sum(ActivityLog.steps), 0))
        .where(ActivityLog.user_id == user.id)
        .where(ActivityLog.deleted_at.is_(None))
        .where(ActivityLog.occurred_on >= start_day)
        .group_by(ActivityLog.occurred_on)
        .order_by(ActivityLog.occurred_on.asc())
    ).all()

    by_day: dict[date, int] = {r[0]: int(r[1] or 0) for r in rows}

    out: list[dict] = []
    for i in range(days):
        d = start_day + timedelta(days=i)
        out.append({"date": d.isoformat(), "steps": int(by_day.get(d, 0))})
    return out


@router.get(
    "/timeseries/weight",
    summary="Weight time-series",
    description="Returns measured weight points for the current user over a time window (sparse series).",
    operation_id="analytics_weight_timeseries",
)
def analytics_weight_timeseries(
    days: int = Query(90, ge=1, le=3650, description="Lookback window in days."),
    user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return weight points as [{measured_at, weight_kg}]."""
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.execute(
            select(BodyMetric.measured_at, BodyMetric.weight_kg)
            .where(BodyMetric.user_id == user.id)
            .where(BodyMetric.deleted_at.is_(None))
            .where(BodyMetric.measured_at >= since)
            .where(BodyMetric.weight_kg.is_not(None))
            .order_by(BodyMetric.measured_at.asc())
        )
        .all()
    )
    return [
        {"measured_at": r[0].isoformat(), "weight_kg": float(r[1]) if r[1] is not None else None}
        for r in rows
    ]


@router.get(
    "/timeseries/workouts",
    summary="Workouts time-series",
    description="Returns daily workout counts for the current user over a time window.",
    operation_id="analytics_workouts_timeseries",
)
def analytics_workouts_timeseries(
    days: int = Query(28, ge=1, le=365, description="Lookback window in days."),
    user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return daily workout counts as [{date, workouts_count}]."""
    start_day = date.today() - timedelta(days=days - 1)
    since_dt = datetime.utcnow() - timedelta(days=days)

    # Aggregate by date(workout.started_at)
    rows = db.execute(
        select(func.date(WorkoutLog.started_at), func.count())
        .select_from(WorkoutLog)
        .where(WorkoutLog.user_id == user.id)
        .where(WorkoutLog.deleted_at.is_(None))
        .where(WorkoutLog.started_at >= since_dt)
        .group_by(func.date(WorkoutLog.started_at))
        .order_by(func.date(WorkoutLog.started_at).asc())
    ).all()

    by_day: dict[str, int] = {str(r[0]): int(r[1] or 0) for r in rows if r[0] is not None}

    out: list[dict] = []
    for i in range(days):
        d = start_day + timedelta(days=i)
        out.append({"date": d.isoformat(), "workouts_count": int(by_day.get(d.isoformat(), 0))})
    return out


@router.get(
    "/streaks",
    summary="Streak analytics",
    description="Returns simple workout/steps streak counters for current user.",
    operation_id="analytics_streaks",
)
def analytics_streaks(
    steps_goal: int = Query(8000, ge=0, le=100000, description="Daily steps threshold for steps streak."),
    user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Compute basic streaks. Keeps logic intentionally simple for CI-safe backend usage."""
    today = date.today()

    # Pull last 60 days to compute streaks quickly.
    start_day = today - timedelta(days=60)

    # Workouts by day
    workout_days = db.execute(
        select(func.date(WorkoutLog.started_at))
        .select_from(WorkoutLog)
        .where(WorkoutLog.user_id == user.id)
        .where(WorkoutLog.deleted_at.is_(None))
        .where(WorkoutLog.started_at >= datetime.utcnow() - timedelta(days=60))
        .group_by(func.date(WorkoutLog.started_at))
    ).all()
    workout_day_set = {str(r[0]) for r in workout_days if r[0] is not None}

    # Steps by day
    step_rows = db.execute(
        select(ActivityLog.occurred_on, func.coalesce(func.sum(ActivityLog.steps), 0))
        .select_from(ActivityLog)
        .where(ActivityLog.user_id == user.id)
        .where(ActivityLog.deleted_at.is_(None))
        .where(ActivityLog.occurred_on >= start_day)
        .group_by(ActivityLog.occurred_on)
    ).all()
    steps_by_day: dict[str, int] = {r[0].isoformat(): int(r[1] or 0) for r in step_rows}

    def _compute_streak(predicate_by_day: dict[str, bool]) -> int:
        streak = 0
        for i in range(0, 61):
            d = today - timedelta(days=i)
            if predicate_by_day.get(d.isoformat(), False):
                streak += 1
            else:
                break
        return streak

    workout_pred = defaultdict(bool)
    for d in workout_day_set:
        workout_pred[d] = True

    steps_pred = defaultdict(bool)
    for d_str, val in steps_by_day.items():
        steps_pred[d_str] = val >= steps_goal

    return {
        "workout_streak_days": _compute_streak(workout_pred),
        "steps_streak_days": _compute_streak(steps_pred),
        "steps_goal": steps_goal,
    }
