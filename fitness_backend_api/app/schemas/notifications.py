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
