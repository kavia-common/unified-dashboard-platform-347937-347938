from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.deps import get_db
from app.models.fitness import NotificationDelivery, NotificationSchedule
from app.models.user import AppUser
from app.schemas.common import OkResponse
from app.schemas.notifications import (
    NotificationDeliveryResponse,
    NotificationScheduleCreateRequest,
    NotificationScheduleResponse,
    NotificationScheduleUpdateRequest,
)

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


def _load_schedule_owned(db: Session, *, schedule_id: str, user_id: str) -> NotificationSchedule:
    n = db.execute(
        select(NotificationSchedule)
        .where(NotificationSchedule.id == schedule_id)
        .where(NotificationSchedule.user_id == user_id)
        .where(NotificationSchedule.deleted_at.is_(None))
    ).scalar_one_or_none()
    if n is None:
        raise HTTPException(status_code=404, detail="Notification schedule not found")
    return n


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


@router.patch(
    "/{schedule_id}",
    response_model=NotificationScheduleResponse,
    summary="Update notification schedule",
    description="Patch/update a reminder/notification schedule for the current user.",
    operation_id="update_notification_schedule",
)
def update_notification_schedule(
    schedule_id: str,
    req: NotificationScheduleUpdateRequest,
    user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationScheduleResponse:
    """Update a notification schedule."""
    n = _load_schedule_owned(db, schedule_id=schedule_id, user_id=str(user.id))
    payload = req.model_dump(exclude_unset=True)

    for k, v in payload.items():
        if k == "meta" and v is None:
            continue
        setattr(n, k, v)

    n.updated_at = func.now()
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


@router.delete(
    "/{schedule_id}",
    response_model=OkResponse,
    summary="Delete notification schedule",
    description="Soft-delete a schedule (current user only).",
    operation_id="delete_notification_schedule",
)
def delete_notification_schedule(
    schedule_id: str,
    user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OkResponse:
    """Soft-delete a notification schedule."""
    n = _load_schedule_owned(db, schedule_id=schedule_id, user_id=str(user.id))
    n.deleted_at = datetime.utcnow()
    n.updated_at = func.now()
    db.commit()
    return OkResponse(ok=True)


@router.get(
    "/{schedule_id}/deliveries",
    response_model=list[NotificationDeliveryResponse],
    summary="List notification deliveries",
    description="List delivery history rows for a given schedule (current user only).",
    operation_id="list_notification_deliveries",
)
def list_notification_deliveries(
    schedule_id: str,
    limit: int = Query(50, ge=1, le=200, description="Max rows to return."),
    user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NotificationDeliveryResponse]:
    """List deliveries for the current user's schedule."""
    _ = _load_schedule_owned(db, schedule_id=schedule_id, user_id=str(user.id))

    rows = (
        db.execute(
            select(NotificationDelivery)
            .where(NotificationDelivery.schedule_id == schedule_id)
            .where(NotificationDelivery.user_id == user.id)
            .order_by(NotificationDelivery.delivered_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )

    # Not all additive columns exist in ORM models yet; use getattr for safety.
    return [
        NotificationDeliveryResponse(
            id=str(d.id),
            schedule_id=str(d.schedule_id) if d.schedule_id else None,
            delivered_at=d.delivered_at,
            channel=d.channel,
            status=d.status,
            error=d.error,
            payload=d.payload or {},
            provider_message_id=getattr(d, "provider_message_id", None),
            attempt=getattr(d, "attempt", None),
            delivered_to=getattr(d, "delivered_to", None),
        )
        for d in rows
    ]
