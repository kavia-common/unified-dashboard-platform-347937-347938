from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.deps import get_db
from app.models.fitness import PlannedSessionExercise, PlannedWorkoutSession, WorkoutLog, WorkoutLogExercise, WorkoutLogSet, WorkoutPlan
from app.models.user import AppUser
from app.schemas.plan_execution import (
    PlannedSessionStatusResponse,
    StartedPlannedSessionResponse,
    UpdatePlannedSessionStatusRequest,
)
from app.schemas.plans import (
    PlanCreateRequest,
    PlanResponse,
    PlannedSessionCreateRequest,
    PlannedSessionResponse,
)

router = APIRouter(prefix="/api/plans", tags=["Plans"])


@router.get(
    "",
    response_model=list[PlanResponse],
    summary="List plans",
    description="List workout plans for the current user.",
    operation_id="list_plans",
)
def list_plans(user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[PlanResponse]:
    """List plans for current user."""
    rows = db.execute(
        select(WorkoutPlan).where(WorkoutPlan.user_id == user.id).where(WorkoutPlan.deleted_at.is_(None)).order_by(WorkoutPlan.created_at.desc())
    ).scalars()
    return [
        PlanResponse(
            id=str(p.id),
            title=p.title,
            description=p.description,
            start_date=p.start_date,
            end_date=p.end_date,
            is_active=p.is_active,
            source=p.source,
            source_meta=p.source_meta,
        )
        for p in rows
    ]


@router.post(
    "",
    response_model=PlanResponse,
    summary="Create plan",
    description="Create a workout plan for the current user.",
    operation_id="create_plan",
)
def create_plan(req: PlanCreateRequest, user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> PlanResponse:
    """Create a workout plan."""
    p = WorkoutPlan(
        user_id=user.id,
        title=req.title,
        description=req.description,
        start_date=req.start_date,
        end_date=req.end_date,
        is_active=True,
        source=req.source,
        source_meta=req.source_meta,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return PlanResponse(
        id=str(p.id),
        title=p.title,
        description=p.description,
        start_date=p.start_date,
        end_date=p.end_date,
        is_active=p.is_active,
        source=p.source,
        source_meta=p.source_meta,
    )


@router.get(
    "/{plan_id}/sessions",
    response_model=list[PlannedSessionResponse],
    summary="List planned sessions",
    description="List scheduled sessions for a plan.",
    operation_id="list_plan_sessions",
)
def list_plan_sessions(plan_id: str, user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[PlannedSessionResponse]:
    """List planned sessions for a specific plan belonging to the current user."""
    plan = db.execute(select(WorkoutPlan).where(WorkoutPlan.id == plan_id).where(WorkoutPlan.user_id == user.id)).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    rows = db.execute(
        select(PlannedWorkoutSession)
        .where(PlannedWorkoutSession.workout_plan_id == plan.id)
        .where(PlannedWorkoutSession.deleted_at.is_(None))
        .order_by(PlannedWorkoutSession.scheduled_date.asc())
    ).scalars()
    return [
        PlannedSessionResponse(
            id=str(s.id),
            workout_plan_id=str(s.workout_plan_id),
            scheduled_date=s.scheduled_date,
            title=s.title,
            notes=s.notes,
            workout_template_id=str(s.workout_template_id) if s.workout_template_id else None,
            status=s.status,
        )
        for s in rows
    ]


@router.post(
    "/{plan_id}/sessions",
    response_model=PlannedSessionResponse,
    summary="Create planned session",
    description="Create a scheduled workout session inside a plan.",
    operation_id="create_plan_session",
)
def create_plan_session(
    plan_id: str,
    req: PlannedSessionCreateRequest,
    user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlannedSessionResponse:
    """Create a planned session for the plan."""
    plan = db.execute(select(WorkoutPlan).where(WorkoutPlan.id == plan_id).where(WorkoutPlan.user_id == user.id)).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    s = PlannedWorkoutSession(
        workout_plan_id=plan.id,
        user_id=user.id,
        scheduled_date=req.scheduled_date,
        title=req.title,
        notes=req.notes,
        workout_template_id=req.workout_template_id,
        status=req.status or "planned",
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return PlannedSessionResponse(
        id=str(s.id),
        workout_plan_id=str(s.workout_plan_id),
        scheduled_date=s.scheduled_date,
        title=s.title,
        notes=s.notes,
        workout_template_id=str(s.workout_template_id) if s.workout_template_id else None,
        status=s.status,
    )


@router.post(
    "/sessions/{session_id}/start",
    response_model=StartedPlannedSessionResponse,
    summary="Start a planned session",
    description=(
        "Creates a `workout_log` linked to the planned session and pre-fills `workout_log_exercise` + "
        "`workout_log_set` rows from `planned_session_exercise.target`."
    ),
    operation_id="start_planned_session",
)
def start_planned_session(
    session_id: str,
    user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StartedPlannedSessionResponse:
    """Start a planned workout session by creating a prefilled workout log.

    Behavior:
    - Validates the session belongs to the current user and is not deleted.
    - Idempotent-ish: if a workout_log already exists for this planned session (and is not deleted),
      returns that log id instead of creating a new one.
    - Creates workout_log_exercise rows in the same order as planned_session_exercise.position.
    - For each planned exercise, creates placeholder sets based on target["sets"] (or target["set_count"])
      and target["reps"] (or target["rep_range"]).
    - Marks planned session status to 'in_progress' when started.
    """
    s = db.execute(
        select(PlannedWorkoutSession)
        .where(PlannedWorkoutSession.id == session_id)
        .where(PlannedWorkoutSession.user_id == user.id)
        .where(PlannedWorkoutSession.deleted_at.is_(None))
    ).scalar_one_or_none()
    if s is None:
        raise HTTPException(status_code=404, detail="Planned session not found")

    # If already started (log exists), return it.
    existing_log = db.execute(
        select(WorkoutLog)
        .where(WorkoutLog.user_id == user.id)
        .where(WorkoutLog.planned_session_id == s.id)
        .where(WorkoutLog.deleted_at.is_(None))
        .order_by(WorkoutLog.started_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if existing_log is not None:
        return StartedPlannedSessionResponse(
            workout_log_id=str(existing_log.id),
            planned_session_id=str(s.id),
        )

    w = WorkoutLog(
        user_id=user.id,
        planned_session_id=s.id,
        title=s.title,
        notes=s.notes,
        # started_at server_default now()
    )
    db.add(w)
    db.flush()  # assign w.id

    planned_exercises = db.execute(
        select(PlannedSessionExercise)
        .where(PlannedSessionExercise.planned_session_id == s.id)
        .order_by(PlannedSessionExercise.position.asc())
    ).scalars()

    for pex in planned_exercises:
        target = pex.target or {}
        # Planned "position" is already 0-based in our DB model usage.
        wex = WorkoutLogExercise(
            workout_log_id=w.id,
            exercise_id=pex.exercise_id,
            position=int(pex.position),
            notes=target.get("notes"),
        )
        db.add(wex)
        db.flush()  # assign wex.id

        # Heuristics for set count + per-set reps:
        set_count = target.get("sets")
        if set_count is None:
            set_count = target.get("set_count")
        try:
            set_count_int = int(set_count) if set_count is not None else 0
        except Exception:
            set_count_int = 0

        reps_val = target.get("reps")
        if reps_val is None:
            # If rep_range is like {"min": 8, "max": 12}, prefer min as a starting point.
            rep_range = target.get("rep_range") or {}
            reps_val = rep_range.get("min")

        for i in range(max(set_count_int, 0)):
            ws = WorkoutLogSet(
                workout_log_exercise_id=wex.id,
                set_number=i + 1,
                reps=int(reps_val) if reps_val is not None else None,
                weight_kg=target.get("weight_kg"),
                duration_seconds=target.get("duration_seconds"),
                distance_meters=target.get("distance_meters"),
                is_warmup=bool(target.get("is_warmup", False)),
                rpe=target.get("rpe"),
                notes=None,
            )
            db.add(ws)

    # Move session to in_progress (best-effort). Don't block if status was already completed/skipped.
    if (s.status or "planned") in ("planned", "in_progress"):
        s.status = "in_progress"
        s.updated_at = func.now()

    db.commit()
    db.refresh(w)

    return StartedPlannedSessionResponse(workout_log_id=str(w.id), planned_session_id=str(s.id))


@router.patch(
    "/sessions/{session_id}/status",
    response_model=PlannedSessionStatusResponse,
    summary="Update planned session status",
    description="Updates a planned workout session status (e.g. completed/skipped).",
    operation_id="update_planned_session_status",
)
def update_planned_session_status(
    session_id: str,
    req: UpdatePlannedSessionStatusRequest,
    user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlannedSessionStatusResponse:
    """Update planned workout session status for the current user."""
    allowed = {"planned", "in_progress", "completed", "skipped", "cancelled"}
    if req.status not in allowed:
        raise HTTPException(status_code=422, detail=f"Invalid status: {req.status}")

    s = db.execute(
        select(PlannedWorkoutSession)
        .where(PlannedWorkoutSession.id == session_id)
        .where(PlannedWorkoutSession.user_id == user.id)
        .where(PlannedWorkoutSession.deleted_at.is_(None))
    ).scalar_one_or_none()
    if s is None:
        raise HTTPException(status_code=404, detail="Planned session not found")

    s.status = req.status
    s.updated_at = func.now()
    db.commit()
    db.refresh(s)
    return PlannedSessionStatusResponse(planned_session_id=str(s.id), status=s.status)
