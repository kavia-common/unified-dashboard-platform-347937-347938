"""
End-to-end smoke test for the backend Plan-to-Workout execution flow.

This test is designed to be CI-safe:
- No real Firebase Admin credentials required (we override get_current_user).
- No real Postgres required (we override get_db to use an in-memory SQLite database).
- Exercises/plan/session/log data are created directly in the test DB, then validated
  through the public API endpoints.
"""

from __future__ import annotations

from datetime import date
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.auth import get_current_user
from app.db.deps import get_db
from app.main import app
from app.models.base import Base
from app.models.fitness import (
    Exercise,
    PlannedSessionExercise,
    PlannedWorkoutSession,
    WorkoutLogExercise,
    WorkoutLogSet,
    WorkoutPlan,
)
from app.models.user import AppUser


@pytest.fixture()
def client_and_db() -> Generator[tuple[TestClient, Session], None, None]:
    """
    Provide a TestClient and an isolated DB session wired into FastAPI dependencies.

    We use in-memory SQLite to keep the test self-contained and fast. Because the app's
    ORM models use Postgres-specific column types (UUID, JSONB, ARRAY), we create only
    the small subset of tables needed for this smoke flow via `__table__.create(...)`.
    """
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    # Create only the required tables (avoids issues with PG-specific types elsewhere).
    # Note: These tables contain PG-specific column types too, but SQLAlchemy can often
    # still DDL them for SQLite sufficiently for test usage of basic columns.
    # If CI ever fails here, the correct fix is to add SQLite-friendly test metadata,
    # but for now we keep this smoke test minimal and targeted.
    for model in (AppUser, Exercise, WorkoutPlan, PlannedWorkoutSession, PlannedSessionExercise, WorkoutLogExercise, WorkoutLogSet):
        model.__table__.create(bind=engine, checkfirst=True)

    db = TestingSessionLocal()

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db
        finally:
            # Keep session open for the duration of the fixture so the client can reuse it.
            pass

    def override_get_current_user() -> AppUser:
        """
        Override auth to avoid Firebase.

        We create a deterministic user row and always return it.
        """
        user = db.execute(select(AppUser).where(AppUser.firebase_uid == "test_uid")).scalar_one_or_none()
        if user is None:
            user = AppUser(
                firebase_uid="test_uid",
                email="test@example.com",
                display_name="Test User",
                photo_url=None,
                is_admin=False,
                is_disabled=False,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as client:
        yield client, db

    db.close()
    app.dependency_overrides.clear()


def test_e2e_plan_to_workout_flow_start_prefill_and_update_status(client_and_db: tuple[TestClient, Session]) -> None:
    """
    Smoke flow:
    1) Create a plan via POST /api/plans
    2) Create a planned session via POST /api/plans/{plan_id}/sessions
    3) Create exercises + planned_session_exercise rows directly (the router doesn't expose this yet)
    4) Start the planned session via POST /api/plans/sessions/{session_id}/start
       - verifies a workout_log is created and prefilled with workout_log_exercise + workout_log_set
    5) Update planned session status via PATCH /api/plans/sessions/{session_id}/status
    """
    client, db = client_and_db

    # 1) Create a plan
    resp = client.post(
        "/api/plans",
        json={
            "title": "Test Plan",
            "description": "Plan-to-workout e2e smoke test",
            "start_date": str(date.today()),
            "end_date": None,
            "source": "manual",
            "source_meta": {},
        },
    )
    assert resp.status_code == 200, resp.text
    plan = resp.json()
    assert plan["id"]
    plan_id = plan["id"]
    assert plan["title"] == "Test Plan"

    # 2) Create planned session
    resp = client.post(
        f"/api/plans/{plan_id}/sessions",
        json={
            "scheduled_date": str(date.today()),
            "title": "Session A",
            "notes": "Do the work",
            "workout_template_id": None,
            "status": "planned",
        },
    )
    assert resp.status_code == 200, resp.text
    planned_session = resp.json()
    session_id = planned_session["id"]
    assert planned_session["status"] == "planned"

    # 3) Seed exercises and planned session exercises (targets drive prefill)
    ex1 = Exercise(name="Push-up", description=None, primary_muscle_group="chest")
    ex2 = Exercise(name="Squat", description=None, primary_muscle_group="legs")
    db.add_all([ex1, ex2])
    db.commit()
    db.refresh(ex1)
    db.refresh(ex2)

    # Targets are interpreted by the start endpoint:
    # - set_count from target["sets"] or target["set_count"]
    # - reps from target["reps"] or target["rep_range"]["min"]
    pex1 = PlannedSessionExercise(
        planned_session_id=session_id,
        exercise_id=ex1.id,
        position=0,
        target={"sets": 3, "reps": 10, "notes": "Strict form"},
    )
    pex2 = PlannedSessionExercise(
        planned_session_id=session_id,
        exercise_id=ex2.id,
        position=1,
        target={"set_count": 2, "rep_range": {"min": 8, "max": 12}},
    )
    db.add_all([pex1, pex2])
    db.commit()

    # 4) Start session -> creates workout_log and prefilled exercises/sets
    resp = client.post(f"/api/plans/sessions/{session_id}/start")
    assert resp.status_code == 200, resp.text
    started = resp.json()
    assert started["planned_session_id"] == session_id
    workout_log_id = started["workout_log_id"]
    assert workout_log_id

    # Validate prefilled rows exist in DB with expected counts.
    wex_rows = (
        db.execute(select(WorkoutLogExercise).where(WorkoutLogExercise.workout_log_id == workout_log_id).order_by(WorkoutLogExercise.position.asc()))
        .scalars()
        .all()
    )
    assert len(wex_rows) == 2
    assert wex_rows[0].exercise_id == ex1.id
    assert wex_rows[1].exercise_id == ex2.id

    sets_ex1 = db.execute(select(WorkoutLogSet).where(WorkoutLogSet.workout_log_exercise_id == wex_rows[0].id).order_by(WorkoutLogSet.set_number.asc())).scalars().all()
    sets_ex2 = db.execute(select(WorkoutLogSet).where(WorkoutLogSet.workout_log_exercise_id == wex_rows[1].id).order_by(WorkoutLogSet.set_number.asc())).scalars().all()

    assert len(sets_ex1) == 3
    assert [s.reps for s in sets_ex1] == [10, 10, 10]
    assert [s.set_number for s in sets_ex1] == [1, 2, 3]

    assert len(sets_ex2) == 2
    # rep_range min used as default reps
    assert [s.reps for s in sets_ex2] == [8, 8]
    assert [s.set_number for s in sets_ex2] == [1, 2]

    # 5) Update planned session status -> completed
    resp = client.patch(f"/api/plans/sessions/{session_id}/status", json={"status": "completed"})
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated == {"planned_session_id": session_id, "status": "completed"}
