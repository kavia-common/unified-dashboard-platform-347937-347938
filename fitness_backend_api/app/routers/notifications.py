from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.deps import get_db
from app.models.fitness import NotificationSchedule
from app.models.user import AppUser
from app.schemas.notifications import NotificationScheduleCreateRequest, NotificationScheduleResponse

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=list[NotificationScheduleResponse],
    summary="List notification schedules",
    description="List reminder/notification schedules for the current user.",
    operation_id="list_notification_schedules",
)
def list_notification_schedules(user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[NotificationScheduleResponse]:
    """List notification schedules."""
    rows = db.execute(
        select(NotificationSchedule)
        .where(NotificationSchedule.user_id == user.id)
        .where(NotificationSchedule.deleted_at.is_(None))
        .order_by(NotificationSchedule.created_at.desc())
    ).scalars()
    return [
        NotificationScheduleResponse(
            id=str(n.id),
            notification_type=n.notification_type,
            channel=n.channel,
            title=n.title,
            body=n.body,
            is_enabled=n.is_enabled,
            next_run_at=n.next_run_at,
        )
        for n in rows
    ]


@router.post(
    "",
    response_model=NotificationScheduleResponse,
    summary="Create notification schedule",
    description="Create a reminder/notification schedule for the current user.",
    operation_id="create_notification_schedule",
)
def create_notification_schedule(
    req: NotificationScheduleCreateRequest, user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> NotificationScheduleResponse:
    """Create a notification schedule."""
    n = NotificationSchedule(
        user_id=user.id,
        notification_type=req.notification_type,
        channel=req.channel,
        title=req.title,
        body=req.body,
        cron=req.cron,
        scheduled_at=req.scheduled_at,
        timezone=req.timezone,
        is_enabled=req.is_enabled,
        meta=req.meta,
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return NotificationScheduleResponse(
        id=str(n.id),
        notification_type=n.notification_type,
        channel=n.channel,
        title=n.title,
        body=n.body,
        is_enabled=n.is_enabled,
        next_run_at=n.next_run_at,
    )
