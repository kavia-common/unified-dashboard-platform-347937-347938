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
        select(func.count()).select_from(WorkoutLog).where(WorkoutLog.user_id == user.id).where(WorkoutLog.started_at >= since).where(WorkoutLog.deleted_at.is_(None))
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
