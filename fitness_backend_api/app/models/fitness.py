from __future__ import annotations

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.dialects import DialectARRAYText, DialectJSONB, DialectUUID, uuid_pk_column


class UserGoal(Base):
    __tablename__ = "user_goal"

    id: Mapped[str] = uuid_pk_column()
    user_id: Mapped[str] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    goal_type: Mapped[str] = mapped_column(Text, nullable=False)
    target: Mapped[dict] = mapped_column(DialectJSONB(), nullable=False, server_default="{}")

    start_date: Mapped[object] = mapped_column(Date, nullable=False, server_default=func.current_date())
    end_date: Mapped[object | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Exercise(Base):
    __tablename__ = "exercise"

    id: Mapped[str] = uuid_pk_column()
    created_by: Mapped[str | None] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="SET NULL"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_muscle_group: Mapped[str | None] = mapped_column(Text, nullable=True)
    secondary_muscle_groups: Mapped[list[str]] = mapped_column(DialectARRAYText(), nullable=False, server_default="{}")
    equipment: Mapped[list[str]] = mapped_column(DialectARRAYText(), nullable=False, server_default="{}")
    movement_pattern: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(Text, nullable=True)

    instructions: Mapped[list] = mapped_column(DialectJSONB(), nullable=False, server_default="[]")
    media: Mapped[dict] = mapped_column(DialectJSONB(), nullable=False, server_default="{}")

    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkoutTemplate(Base):
    __tablename__ = "workout_template"

    id: Mapped[str] = uuid_pk_column()
    owner_user_id: Mapped[str | None] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="CASCADE"),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    tags: Mapped[list[str]] = mapped_column(DialectARRAYText(), nullable=False, server_default="{}")
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkoutTemplateExercise(Base):
    __tablename__ = "workout_template_exercise"

    id: Mapped[str] = uuid_pk_column()
    workout_template_id: Mapped[str] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("workout_template.id", ondelete="CASCADE"),
        nullable=False,
    )
    exercise_id: Mapped[str] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("exercise.id", ondelete="RESTRICT"),
        nullable=False,
    )

    position: Mapped[int] = mapped_column(Integer, nullable=False)
    sets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rep_range: Mapped[dict] = mapped_column(DialectJSONB(), nullable=False, server_default="{}")
    weight_kg: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_meters: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    rest_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class WorkoutPlan(Base):
    __tablename__ = "workout_plan"

    id: Mapped[str] = uuid_pk_column()
    user_id: Mapped[str] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[object] = mapped_column(Date, nullable=False, server_default=func.current_date())
    end_date: Mapped[object | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_meta: Mapped[dict] = mapped_column(DialectJSONB(), nullable=False, server_default="{}")

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PlannedWorkoutSession(Base):
    __tablename__ = "planned_workout_session"

    id: Mapped[str] = uuid_pk_column()
    workout_plan_id: Mapped[str] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("workout_plan.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    scheduled_date: Mapped[object] = mapped_column(Date, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    workout_template_id: Mapped[str | None] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("workout_template.id", ondelete="SET NULL"),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="planned")

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PlannedSessionExercise(Base):
    __tablename__ = "planned_session_exercise"

    id: Mapped[str] = uuid_pk_column()
    planned_session_id: Mapped[str] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("planned_workout_session.id", ondelete="CASCADE"),
        nullable=False,
    )
    exercise_id: Mapped[str] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("exercise.id", ondelete="RESTRICT"),
        nullable=False,
    )

    position: Mapped[int] = mapped_column(Integer, nullable=False)
    target: Mapped[dict] = mapped_column(DialectJSONB(), nullable=False, server_default="{}")

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class WorkoutLog(Base):
    __tablename__ = "workout_log"

    id: Mapped[str] = uuid_pk_column()
    user_id: Mapped[str] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    planned_session_id: Mapped[str | None] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("planned_workout_session.id", ondelete="SET NULL"),
        nullable=True,
    )

    started_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    ended_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    rpe: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calories_burned: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkoutLogExercise(Base):
    __tablename__ = "workout_log_exercise"

    id: Mapped[str] = uuid_pk_column()
    workout_log_id: Mapped[str] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("workout_log.id", ondelete="CASCADE"),
        nullable=False,
    )
    exercise_id: Mapped[str] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("exercise.id", ondelete="RESTRICT"),
        nullable=False,
    )

    position: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class WorkoutLogSet(Base):
    __tablename__ = "workout_log_set"

    id: Mapped[str] = uuid_pk_column()
    workout_log_exercise_id: Mapped[str] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("workout_log_exercise.id", ondelete="CASCADE"),
        nullable=False,
    )

    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_meters: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    is_warmup: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    rpe: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id: Mapped[str] = uuid_pk_column()
    user_id: Mapped[str] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    activity_type: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_on: Mapped[object] = mapped_column(Date, nullable=False)

    steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_meters: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    calories_burned: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(DialectJSONB(), nullable=False, server_default="{}")

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BodyMetric(Base):
    __tablename__ = "body_metric"

    id: Mapped[str] = uuid_pk_column()
    user_id: Mapped[str] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    measured_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    weight_kg: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    body_fat_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    measurements: Mapped[dict] = mapped_column(DialectJSONB(), nullable=False, server_default="{}")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProgressPhoto(Base):
    __tablename__ = "progress_photo"

    id: Mapped[str] = uuid_pk_column()
    user_id: Mapped[str] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    taken_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    storage_provider: Mapped[str] = mapped_column(Text, nullable=False, server_default="local")
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Additive migration 002 fields
    meta: Mapped[dict] = mapped_column(DialectJSONB(), nullable=False, server_default="{}")
    mime_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_px: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PersonalRecord(Base):
    __tablename__ = "personal_record"

    id: Mapped[str] = uuid_pk_column()
    user_id: Mapped[str] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exercise_id: Mapped[str | None] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("exercise.id", ondelete="SET NULL"),
        nullable=True,
    )

    pr_type: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[dict] = mapped_column(DialectJSONB(), nullable=False, server_default="{}")
    achieved_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NotificationSchedule(Base):
    __tablename__ = "notification_schedule"

    id: Mapped[str] = uuid_pk_column()
    user_id: Mapped[str] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    notification_type: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False, server_default="in_app")

    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)

    cron: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    last_run_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    meta: Mapped[dict] = mapped_column(DialectJSONB(), nullable=False, server_default="{}")

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NotificationDelivery(Base):
    __tablename__ = "notification_delivery"

    id: Mapped[str] = uuid_pk_column()
    schedule_id: Mapped[str | None] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("notification_schedule.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[str] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    delivered_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="delivered")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    payload: Mapped[dict] = mapped_column(DialectJSONB(), nullable=False, server_default="{}")

    # Additive migration 002 fields
    provider_message_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    delivered_to: Mapped[str | None] = mapped_column(Text, nullable=True)


class ShareArtifact(Base):
    __tablename__ = "share_artifact"

    id: Mapped[str] = uuid_pk_column()
    user_id: Mapped[str] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    artifact_type: Mapped[str] = mapped_column(Text, nullable=False)
    ref_table: Mapped[str | None] = mapped_column(Text, nullable=True)
    ref_id: Mapped[str | None] = mapped_column(DialectUUID(as_uuid=True), nullable=True)

    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    share_token: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    expires_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AdminContent(Base):
    __tablename__ = "admin_content"

    id: Mapped[str] = uuid_pk_column()
    created_by: Mapped[str | None] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="SET NULL"),
        nullable=True,
    )

    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(DialectARRAYText(), nullable=False, server_default="{}")

    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    published_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AppEvent(Base):
    __tablename__ = "app_event"

    id: Mapped[str] = uuid_pk_column()
    user_id: Mapped[str | None] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="SET NULL"),
        nullable=True,
    )

    event_name: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    properties: Mapped[dict] = mapped_column(DialectJSONB(), nullable=False, server_default="{}")
