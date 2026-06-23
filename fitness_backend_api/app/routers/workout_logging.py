from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.deps import get_db
from app.models.fitness import WorkoutLog, WorkoutLogExercise, WorkoutLogSet
from app.models.user import AppUser
from app.schemas.workouts import WorkoutLogCreateRequest, WorkoutLogResponse

router = APIRouter(prefix="/api/workouts", tags=["Workout Logging"])


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
        select(WorkoutLog).where(WorkoutLog.user_id == user.id).where(WorkoutLog.deleted_at.is_(None)).order_by(WorkoutLog.started_at.desc())
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
