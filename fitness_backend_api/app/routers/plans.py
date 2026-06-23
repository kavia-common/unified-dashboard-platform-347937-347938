from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.deps import get_db
from app.models.fitness import PlannedWorkoutSession, WorkoutPlan
from app.models.user import AppUser
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
