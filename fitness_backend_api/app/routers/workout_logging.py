from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.deps import get_db
from app.models.fitness import WorkoutLog, WorkoutLogExercise, WorkoutLogSet
from app.models.user import AppUser
from app.schemas.common import OkResponse
from app.schemas.workouts import (
    WorkoutExerciseOut,
    WorkoutLogCreateRequest,
    WorkoutLogDetailResponse,
    WorkoutLogResponse,
    WorkoutLogUpdateRequest,
    WorkoutSetOut,
)

router = APIRouter(prefix="/api/workouts", tags=["Workout Logging"])


def _load_log_owned(db: Session, *, workout_log_id: str, user_id: str) -> WorkoutLog:
    w = db.execute(
        select(WorkoutLog)
        .where(WorkoutLog.id == workout_log_id)
        .where(WorkoutLog.user_id == user_id)
        .where(WorkoutLog.deleted_at.is_(None))
    ).scalar_one_or_none()
    if w is None:
        raise HTTPException(status_code=404, detail="Workout log not found")
    return w


def _serialize_log_detail(db: Session, w: WorkoutLog) -> WorkoutLogDetailResponse:
    exercises = (
        db.execute(
            select(WorkoutLogExercise)
            .where(WorkoutLogExercise.workout_log_id == w.id)
            .order_by(WorkoutLogExercise.position.asc())
        )
        .scalars()
        .all()
    )

    ex_out: list[WorkoutExerciseOut] = []
    for ex in exercises:
        sets = (
            db.execute(
                select(WorkoutLogSet)
                .where(WorkoutLogSet.workout_log_exercise_id == ex.id)
                .order_by(WorkoutLogSet.set_number.asc())
            )
            .scalars()
            .all()
        )
        set_out = [
            WorkoutSetOut(
                id=str(s.id),
                set_number=s.set_number,
                reps=s.reps,
                weight_kg=float(s.weight_kg) if s.weight_kg is not None else None,
                duration_seconds=s.duration_seconds,
                distance_meters=float(s.distance_meters) if s.distance_meters is not None else None,
                is_warmup=bool(s.is_warmup),
                rpe=s.rpe,
                notes=s.notes,
            )
            for s in sets
        ]
        ex_out.append(
            WorkoutExerciseOut(
                id=str(ex.id),
                exercise_id=str(ex.exercise_id),
                position=int(ex.position),
                notes=ex.notes,
                sets=set_out,
            )
        )

    return WorkoutLogDetailResponse(
        id=str(w.id),
        planned_session_id=str(w.planned_session_id) if w.planned_session_id else None,
        started_at=w.started_at,
        ended_at=w.ended_at,
        title=w.title,
        notes=w.notes,
        rpe=w.rpe,
        calories_burned=float(w.calories_burned) if w.calories_burned is not None else None,
        exercises=ex_out,
    )


@router.get(
    "",
    response_model=list[WorkoutLogResponse],
    summary="List workout logs",
    description="List workout logs for the current user (excluding soft-deleted).",
    operation_id="list_workout_logs",
)
def list_workout_logs(user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[WorkoutLogResponse]:
    """List workout logs for current user."""
    rows = db.execute(
        select(WorkoutLog)
        .where(WorkoutLog.user_id == user.id)
        .where(WorkoutLog.deleted_at.is_(None))
        .order_by(WorkoutLog.started_at.desc())
    ).scalars()
    return [
        WorkoutLogResponse(
            id=str(w.id),
            started_at=w.started_at,
            ended_at=w.ended_at,
            title=w.title,
            notes=w.notes,
            rpe=w.rpe,
        )
        for w in rows
    ]


@router.get(
    "/{workout_log_id}",
    response_model=WorkoutLogDetailResponse,
    summary="Get workout log detail",
    description="Get a single workout log by id including exercises and sets (owner only).",
    operation_id="get_workout_log_detail",
)
def get_workout_log_detail(
    workout_log_id: str,
    user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkoutLogDetailResponse:
    """Get a workout log (detail view) for the current user."""
    w = _load_log_owned(db, workout_log_id=workout_log_id, user_id=str(user.id))
    return _serialize_log_detail(db, w)


@router.post(
    "",
    response_model=WorkoutLogResponse,
    summary="Create workout log",
    description="Create a workout log including exercises and sets.",
    operation_id="create_workout_log",
)
def create_workout_log(req: WorkoutLogCreateRequest, user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> WorkoutLogResponse:
    """Create a workout log (with optional nested exercises/sets)."""
    w = WorkoutLog(
        user_id=user.id,
        planned_session_id=req.planned_session_id,
        started_at=req.started_at,
        ended_at=req.ended_at,
        title=req.title,
        notes=req.notes,
        rpe=req.rpe,
        calories_burned=req.calories_burned,
    )
    db.add(w)
    db.flush()  # assign w.id

    for ex in req.exercises:
        wex = WorkoutLogExercise(
            workout_log_id=w.id,
            exercise_id=ex.exercise_id,
            position=ex.position,
            notes=ex.notes,
        )
        db.add(wex)
        db.flush()
        for s in ex.sets:
            ws = WorkoutLogSet(
                workout_log_exercise_id=wex.id,
                set_number=s.set_number,
                reps=s.reps,
                weight_kg=s.weight_kg,
                duration_seconds=s.duration_seconds,
                distance_meters=s.distance_meters,
                is_warmup=s.is_warmup,
                rpe=s.rpe,
                notes=s.notes,
            )
            db.add(ws)

    db.commit()
    db.refresh(w)
    return WorkoutLogResponse(
        id=str(w.id),
        started_at=w.started_at,
        ended_at=w.ended_at,
        title=w.title,
        notes=w.notes,
        rpe=w.rpe,
    )


@router.patch(
    "/{workout_log_id}",
    response_model=WorkoutLogDetailResponse,
    summary="Update workout log",
    description=(
        "Patch/update a workout log (owner only). If exercises are provided, the workout's exercises and sets are replaced."
    ),
    operation_id="update_workout_log",
)
def update_workout_log(
    workout_log_id: str,
    req: WorkoutLogUpdateRequest,
    user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkoutLogDetailResponse:
    """Update a workout log for the current user."""
    w = _load_log_owned(db, workout_log_id=workout_log_id, user_id=str(user.id))

    payload = req.model_dump(exclude_unset=True)
    # scalar fields
    for key in ("started_at", "ended_at", "title", "notes", "rpe", "calories_burned"):
        if key in payload:
            setattr(w, key, payload[key])

    # replace exercises/sets if provided
    if "exercises" in payload and payload["exercises"] is not None:
        # Delete sets -> exercises (DB cascade for sets is via exercise_id, so delete sets first)
        old_ex = db.execute(select(WorkoutLogExercise).where(WorkoutLogExercise.workout_log_id == w.id)).scalars().all()
        for ex in old_ex:
            db.execute(select(WorkoutLogSet).where(WorkoutLogSet.workout_log_exercise_id == ex.id))
            db.query(WorkoutLogSet).filter(WorkoutLogSet.workout_log_exercise_id == ex.id).delete(synchronize_session=False)
        db.query(WorkoutLogExercise).filter(WorkoutLogExercise.workout_log_id == w.id).delete(synchronize_session=False)

        # Recreate from provided list
        for ex in payload["exercises"]:
            wex = WorkoutLogExercise(
                workout_log_id=w.id,
                exercise_id=ex["exercise_id"],
                position=int(ex["position"]),
                notes=ex.get("notes"),
            )
            db.add(wex)
            db.flush()
            for s in ex.get("sets") or []:
                ws = WorkoutLogSet(
                    workout_log_exercise_id=wex.id,
                    set_number=int(s["set_number"]),
                    reps=s.get("reps"),
                    weight_kg=s.get("weight_kg"),
                    duration_seconds=s.get("duration_seconds"),
                    distance_meters=s.get("distance_meters"),
                    is_warmup=bool(s.get("is_warmup", False)),
                    rpe=s.get("rpe"),
                    notes=s.get("notes"),
                )
                db.add(ws)

    w.updated_at = func.now()
    db.commit()
    db.refresh(w)
    return _serialize_log_detail(db, w)


@router.delete(
    "/{workout_log_id}",
    response_model=OkResponse,
    summary="Delete workout log",
    description="Soft-delete a workout log (owner only).",
    operation_id="delete_workout_log",
)
def delete_workout_log(
    workout_log_id: str,
    user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OkResponse:
    """Soft-delete a workout log for the current user."""
    w = _load_log_owned(db, workout_log_id=workout_log_id, user_id=str(user.id))
    w.deleted_at = datetime.utcnow()
    w.updated_at = func.now()
    db.commit()
    return OkResponse(ok=True)
