from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class NotificationScheduleCreateRequest(BaseModel):
    notification_type: str = Field(..., description="workout_reminder | goal_checkin | streak_nudge | custom")
    channel: str = Field("in_app", description="in_app | push | email")
    title: str | None = None
    body: str | None = None
    cron: str | None = None
    scheduled_at: datetime | None = None
    timezone: str | None = None
    is_enabled: bool = True
    meta: dict = Field(default_factory=dict)


class NotificationScheduleResponse(BaseModel):
    id: str
    notification_type: str
    channel: str
    title: str | None
    body: str | None
    is_enabled: bool
    next_run_at: datetime | None


class NotificationScheduleUpdateRequest(BaseModel):
    """Patch/update a schedule (all fields optional)."""

    notification_type: str | None = Field(None, description="workout_reminder | goal_checkin | streak_nudge | custom")
    channel: str | None = Field(None, description="in_app | push | email")
    title: str | None = None
    body: str | None = None
    cron: str | None = None
    scheduled_at: datetime | None = None
    timezone: str | None = None
    is_enabled: bool | None = None
    meta: dict | None = None


class NotificationDeliveryResponse(BaseModel):
    id: str
    schedule_id: str | None
    delivered_at: datetime
    channel: str
    status: str
    error: str | None
    payload: dict = Field(default_factory=dict)

    # Migration 002 additive fields (nullable in initial schema)
    provider_message_id: str | None = None
    attempt: int | None = None
    delivered_to: str | None = None
