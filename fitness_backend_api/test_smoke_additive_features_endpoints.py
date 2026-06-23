"""
CI-safe smoke tests for newly integrated additive features.

Goals:
- Cover new CRUD/detail endpoints (workouts, notifications, progress) and analytics/admin feed.
- Ensure tests run without real Firebase Admin credentials by overriding auth dependencies.
- Ensure tests run without Postgres by overriding get_db to use in-memory SQLite.

Design notes:
- The ORM models use some Postgres-specific types. Like the existing e2e smoke test,
  we create only the subset of tables required for this smoke suite via
  `model.__table__.create(...)` and use StaticPool to share the in-memory DB across
  sessions.
- We keep the assertions intentionally "smoke-level": validate status codes, key
  fields, and basic side effects (e.g., soft delete hides items from list).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

from app.core.auth import get_current_user, require_admin
from app.db.deps import get_db
from app.main import app
from app.models.fitness import (
    AdminContent,
    ActivityLog,
    BodyMetric,
    Exercise,
    NotificationDelivery,
    NotificationSchedule,
    PersonalRecord,
    ProgressPhoto,
    WorkoutLog,
    WorkoutLogExercise,
    WorkoutLogSet,
)
from app.models.user import AppUser


@pytest.fixture()
def client_db_and_users() -> Generator[tuple[TestClient, Session, AppUser, AppUser, object], None, None]:
    """
    Provide a TestClient, DB session, and two users (normal + admin), wired via overrides.
    Also provides a small helper for switching the "current user" used by auth overrides.

    Returns:
        (client, db, normal_user, admin_user, set_user)
    """
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    # Create only tables needed for this smoke suite.
    for model in (
        AppUser,
        Exercise,
        WorkoutLog,
        WorkoutLogExercise,
        WorkoutLogSet,
        NotificationSchedule,
        NotificationDelivery,
        BodyMetric,
        PersonalRecord,
        ProgressPhoto,
        ActivityLog,
        AdminContent,
    ):
        model.__table__.create(bind=engine, checkfirst=True)

    db = TestingSessionLocal()

    # Seed users once.
    normal_user = AppUser(
        firebase_uid="uid_normal",
        email="normal@example.com",
        display_name="Normal User",
        photo_url=None,
        is_admin=False,
        is_disabled=False,
    )
    admin_user = AppUser(
        firebase_uid="uid_admin",
        email="admin@example.com",
        display_name="Admin User",
        photo_url=None,
        is_admin=True,
        is_disabled=False,
    )
    db.add_all([normal_user, admin_user])
    db.commit()
    db.refresh(normal_user)
    db.refresh(admin_user)

    # Default auth override: normal user
    current_user_holder: dict[str, AppUser] = {"user": normal_user}

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db
        finally:
            # Keep open for duration of fixture.
            pass

    def override_get_current_user() -> AppUser:
        return current_user_holder["user"]

    def override_require_admin() -> AppUser:
        u = current_user_holder["user"]
        if not u.is_admin:
            # Mirror production behavior: 403
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
        return u

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[require_admin] = override_require_admin

    with TestClient(app) as client:
        def set_user(u: AppUser) -> None:
            """Set the current user used by auth dependency overrides for this client."""
            current_user_holder["user"] = u

        yield client, db, normal_user, admin_user, set_user

    db.close()
    app.dependency_overrides.clear()


def test_workout_log_detail_update_delete_smoke(
    client_db_and_users: tuple[TestClient, Session, AppUser, AppUser, object],
) -> None:
    """Workout log: create -> get detail -> patch update -> delete -> list excludes."""
    client, db, normal_user, _admin_user, set_user = client_db_and_users
    set_user(normal_user)  # type: ignore[operator]

    # Seed an Exercise so we can reference exercise_id.
    ex = Exercise(name="Bench Press", description=None, primary_muscle_group="chest")
    db.add(ex)
    db.commit()
    db.refresh(ex)

    # Create workout log (with nested exercises/sets)
    resp = client.post(
        "/api/workouts",
        json={
            "planned_session_id": None,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": None,
            "title": "Push Day",
            "notes": "Initial notes",
            "rpe": 7,
            "calories_burned": 120.5,
            "exercises": [
                {
                    "exercise_id": str(ex.id),
                    "position": 0,
                    "notes": "Keep shoulder packed",
                    "sets": [{"set_number": 1, "reps": 8, "weight_kg": 60.0, "is_warmup": False}],
                }
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    created = resp.json()
    workout_log_id = created["id"]
    assert created["title"] == "Push Day"

    # Detail
    resp = client.get(f"/api/workouts/{workout_log_id}")
    assert resp.status_code == 200, resp.text
    detail = resp.json()
    assert detail["id"] == workout_log_id
    assert detail["title"] == "Push Day"
    assert len(detail["exercises"]) == 1
    assert detail["exercises"][0]["exercise_id"] == str(ex.id)
    assert len(detail["exercises"][0]["sets"]) == 1

    # Patch: update scalar fields and replace exercises/sets
    resp = client.patch(
        f"/api/workouts/{workout_log_id}",
        json={
            "title": "Push Day (Updated)",
            "notes": "Updated notes",
            "rpe": 8,
            "exercises": [
                {
                    "exercise_id": str(ex.id),
                    "position": 0,
                    "notes": "Updated exercise note",
                    "sets": [
                        {"set_number": 1, "reps": 5, "weight_kg": 70.0, "is_warmup": False},
                        {"set_number": 2, "reps": 5, "weight_kg": 70.0, "is_warmup": False},
                    ],
                }
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    patched = resp.json()
    assert patched["title"] == "Push Day (Updated)"
    assert len(patched["exercises"]) == 1
    assert len(patched["exercises"][0]["sets"]) == 2
    assert [s["reps"] for s in patched["exercises"][0]["sets"]] == [5, 5]

    # List contains it
    resp = client.get("/api/workouts")
    assert resp.status_code == 200, resp.text
    logs = resp.json()
    assert any(w["id"] == workout_log_id for w in logs)

    # Delete
    resp = client.delete(f"/api/workouts/{workout_log_id}")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"ok": True}

    # Detail now 404
    resp = client.get(f"/api/workouts/{workout_log_id}")
    assert resp.status_code == 404

    # List excludes deleted
    resp = client.get("/api/workouts")
    assert resp.status_code == 200
    logs = resp.json()
    assert all(w["id"] != workout_log_id for w in logs)


def test_notifications_update_delete_and_delivery_history_smoke(
    client_db_and_users: tuple[TestClient, Session, AppUser, AppUser, object],
) -> None:
    """Notifications: create schedule -> patch -> seed delivery -> list deliveries -> delete -> list excludes."""
    client, db, normal_user, _admin_user, set_user = client_db_and_users
    set_user(normal_user)  # type: ignore[operator]

    # Create schedule
    resp = client.post(
        "/api/notifications",
        json={
            "notification_type": "workout_reminder",
            "channel": "in_app",
            "title": "Train today",
            "body": "Don't forget your session",
            "cron": "0 8 * * *",
            "scheduled_at": None,
            "timezone": "UTC",
            "is_enabled": True,
            "meta": {"source": "test"},
        },
    )
    assert resp.status_code == 200, resp.text
    schedule = resp.json()
    schedule_id = schedule["id"]
    assert schedule["is_enabled"] is True

    # Patch schedule
    resp = client.patch(
        f"/api/notifications/{schedule_id}",
        json={"title": "Train today (updated)", "is_enabled": False},
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["id"] == schedule_id
    assert updated["title"] == "Train today (updated)"
    assert updated["is_enabled"] is False

    # Seed a delivery row directly (router only lists)
    d = NotificationDelivery(
        schedule_id=schedule_id,
        user_id=normal_user.id,
        delivered_at=datetime.now(timezone.utc),
        channel="in_app",
        status="delivered",
        error=None,
        payload={"hello": "world"},
        provider_message_id="prov-1",
        attempt=1,
        delivered_to="in_app",
    )
    db.add(d)
    db.commit()

    # List deliveries
    resp = client.get(f"/api/notifications/{schedule_id}/deliveries?limit=50")
    assert resp.status_code == 200, resp.text
    deliveries = resp.json()
    assert len(deliveries) == 1
    assert deliveries[0]["schedule_id"] == schedule_id
    assert deliveries[0]["payload"] == {"hello": "world"}
    assert deliveries[0]["provider_message_id"] == "prov-1"

    # Delete schedule
    resp = client.delete(f"/api/notifications/{schedule_id}")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"ok": True}

    # List schedules excludes deleted
    resp = client.get("/api/notifications")
    assert resp.status_code == 200, resp.text
    schedules = resp.json()
    assert all(s["id"] != schedule_id for s in schedules)


def test_progress_metrics_prs_and_photos_crud_smoke(
    client_db_and_users: tuple[TestClient, Session, AppUser, AppUser, object],
) -> None:
    """Progress: metric create/patch/delete; PR create/patch/delete; photo create/list/delete."""
    client, db, normal_user, _admin_user, set_user = client_db_and_users
    set_user(normal_user)  # type: ignore[operator]

    # Metric create
    resp = client.post(
        "/api/progress/metrics",
        json={
            "measured_at": datetime.now(timezone.utc).isoformat(),
            "weight_kg": 80.2,
            "body_fat_pct": 20.5,
            "measurements": {"waist_cm": 85},
            "notes": "baseline",
        },
    )
    assert resp.status_code == 200, resp.text
    metric = resp.json()
    metric_id = metric["id"]
    assert metric["measurements"]["waist_cm"] == 85

    # Metric patch
    resp = client.patch(f"/api/progress/metrics/{metric_id}", json={"weight_kg": 79.9})
    assert resp.status_code == 200, resp.text
    metric2 = resp.json()
    assert metric2["id"] == metric_id
    assert metric2["weight_kg"] == 79.9

    # Metric delete
    resp = client.delete(f"/api/progress/metrics/{metric_id}")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"ok": True}

    # PR create (exercise_id optional; we include for realism)
    ex = Exercise(name="Deadlift", description=None, primary_muscle_group="back")
    db.add(ex)
    db.commit()
    db.refresh(ex)

    resp = client.post(
        "/api/progress/prs",
        json={
            "exercise_id": str(ex.id),
            "pr_type": "1rm",
            "value": {"weight_kg": 140.0},
            "achieved_at": datetime.now(timezone.utc).isoformat(),
            "notes": "solid",
        },
    )
    assert resp.status_code == 200, resp.text
    pr = resp.json()
    pr_id = pr["id"]
    assert pr["pr_type"] == "1rm"

    # PR patch
    resp = client.patch(f"/api/progress/prs/{pr_id}", json={"value": {"weight_kg": 142.5}})
    assert resp.status_code == 200, resp.text
    pr2 = resp.json()
    assert pr2["id"] == pr_id
    assert pr2["value"] == {"weight_kg": 142.5}

    # PR delete
    resp = client.delete(f"/api/progress/prs/{pr_id}")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"ok": True}

    # Photo create/list/delete
    resp = client.post(
        "/api/progress/photos",
        json={
            "taken_at": datetime.now(timezone.utc).isoformat(),
            "storage_provider": "local",
            "object_key": "photos/test1.jpg",
            "url": "https://example.com/photos/test1.jpg",
            "caption": "Week 1",
            "meta": {"lighting": "ok"},
            "mime_type": "image/jpeg",
            "file_size_bytes": 1234,
            "width_px": 640,
            "height_px": 480,
        },
    )
    assert resp.status_code == 200, resp.text
    photo = resp.json()
    photo_id = photo["id"]
    assert photo["object_key"] == "photos/test1.jpg"
    assert photo["meta"]["lighting"] == "ok"

    resp = client.get("/api/progress/photos")
    assert resp.status_code == 200, resp.text
    photos = resp.json()
    assert any(p["id"] == photo_id for p in photos)

    resp = client.delete(f"/api/progress/photos/{photo_id}")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"ok": True}

    resp = client.get("/api/progress/photos")
    assert resp.status_code == 200
    photos = resp.json()
    assert all(p["id"] != photo_id for p in photos)


def test_analytics_timeseries_and_streaks_smoke(
    client_db_and_users: tuple[TestClient, Session, AppUser, AppUser, object],
) -> None:
    """Analytics: seed activity/workout/weight -> summary + timeseries + streaks respond with expected shapes."""
    client, db, normal_user, _admin_user, set_user = client_db_and_users
    set_user(normal_user)  # type: ignore[operator]

    # Seed steps across the last 3 days (including today).
    today = date.today()
    for i, steps in enumerate([9000, 8500, 2000]):
        d = today - timedelta(days=i)
        db.add(
            ActivityLog(
                user_id=normal_user.id,
                activity_type="steps",
                occurred_on=d,
                steps=steps,
                duration_minutes=None,
                distance_meters=None,
                calories_burned=None,
                source="test",
                meta={},
            )
        )

    # Seed a workout today to influence workouts timeseries/streak.
    db.add(
        WorkoutLog(
            user_id=normal_user.id,
            planned_session_id=None,
            started_at=datetime.now(timezone.utc),
            ended_at=None,
            title="Test Workout",
            notes=None,
            rpe=None,
            calories_burned=None,
        )
    )

    # Seed a weight metric (yesterday)
    db.add(
        BodyMetric(
            user_id=normal_user.id,
            measured_at=datetime.now(timezone.utc) - timedelta(days=1),
            weight_kg=81.1,
            body_fat_pct=None,
            measurements={},
            notes=None,
        )
    )
    db.commit()

    # Summary
    resp = client.get("/api/analytics/summary?days=7")
    assert resp.status_code == 200, resp.text
    summary = resp.json()
    assert summary["window_days"] == 7
    assert summary["workouts_count"] >= 1
    assert summary["steps_sum"] >= 0
    assert summary["latest_weight_kg"] is not None

    # Steps timeseries (7 days)
    resp = client.get("/api/analytics/timeseries/steps?days=7")
    assert resp.status_code == 200, resp.text
    series = resp.json()
    assert isinstance(series, list)
    assert len(series) == 7
    assert "date" in series[0] and "steps" in series[0]

    # Workouts timeseries (7 days)
    resp = client.get("/api/analytics/timeseries/workouts?days=7")
    assert resp.status_code == 200, resp.text
    wseries = resp.json()
    assert isinstance(wseries, list)
    assert len(wseries) == 7
    assert "date" in wseries[0] and "workouts_count" in wseries[0]

    # Weight timeseries (sparse)
    resp = client.get("/api/analytics/timeseries/weight?days=30")
    assert resp.status_code == 200, resp.text
    weight_series = resp.json()
    assert isinstance(weight_series, list)
    assert any(p["weight_kg"] is not None for p in weight_series)

    # Streaks: with steps_goal=8000, today's steps=9000 => steps streak at least 1
    resp = client.get("/api/analytics/streaks?steps_goal=8000")
    assert resp.status_code == 200, resp.text
    streaks = resp.json()
    assert "workout_streak_days" in streaks
    assert "steps_streak_days" in streaks
    assert streaks["steps_goal"] == 8000
    assert streaks["steps_streak_days"] >= 1
    assert streaks["workout_streak_days"] >= 1


def test_admin_public_content_feed_smoke(
    client_db_and_users: tuple[TestClient, Session, AppUser, AppUser, object],
) -> None:
    """Admin content: seed published content -> /api/public/feed returns it without auth."""
    client, db, normal_user, admin_user, set_user = client_db_and_users

    # Seed content via DB so the test doesn't depend on admin auth correctness to validate feed.
    published_at = datetime.now(timezone.utc) - timedelta(hours=1)
    c_pub = AdminContent(
        created_by=admin_user.id,
        content_type="tip",
        title="Stay hydrated",
        slug="stay-hydrated",
        summary="Drink water regularly.",
        body_markdown="Hydration matters.",
        tags=["health"],
        is_published=True,
        published_at=published_at,
    )
    c_draft = AdminContent(
        created_by=admin_user.id,
        content_type="article",
        title="Draft only",
        slug="draft-only",
        summary=None,
        body_markdown="Not published.",
        tags=[],
        is_published=False,
        published_at=None,
    )
    db.add_all([c_pub, c_draft])
    db.commit()

    # Public endpoint should not require auth; but our overrides might still be present.
    # Ensure normal user is set (should be irrelevant for public router).
    set_user(normal_user)  # type: ignore[operator]

    resp = client.get("/api/public/feed?limit=10")
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert any(i["slug"] == "stay-hydrated" for i in items)
    assert all(i["slug"] != "draft-only" for i in items)
    # Smoke shape checks
    first = items[0]
    assert {"id", "content_type", "title", "slug", "summary", "tags", "published_at"}.issubset(set(first.keys()))
