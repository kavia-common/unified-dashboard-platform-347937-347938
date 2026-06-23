from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.deps import get_db
from app.models.fitness import UserGoal
from app.models.user import AppUser
from app.schemas.goals import GoalCreateRequest, GoalResponse

router = APIRouter(prefix="/api/goals", tags=["Goals"])


@router.get(
    "",
    response_model=list[GoalResponse],
    summary="List goals",
    description="List all goals for the current user (excluding soft-deleted).",
    operation_id="list_goals",
)
def list_goals(user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[GoalResponse]:
    """List goals for the current user."""
    rows = db.execute(
        select(UserGoal).where(UserGoal.user_id == user.id).where(UserGoal.deleted_at.is_(None)).order_by(UserGoal.created_at.desc())
    ).scalars()
    return [
        GoalResponse(
            id=str(g.id),
            goal_type=g.goal_type,
            target=g.target,
            start_date=g.start_date,
            end_date=g.end_date,
            is_active=g.is_active,
        )
        for g in rows
    ]


@router.post(
    "",
    response_model=GoalResponse,
    summary="Create goal",
    description="Create a new goal for the current user.",
    operation_id="create_goal",
)
def create_goal(req: GoalCreateRequest, user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> GoalResponse:
    """Create a goal record."""
    g = UserGoal(
        user_id=user.id,
        goal_type=req.goal_type,
        target=req.target,
        start_date=req.start_date,
        end_date=req.end_date,
        is_active=True,
    )
    db.add(g)
    db.commit()
    db.refresh(g)
    return GoalResponse(id=str(g.id), goal_type=g.goal_type, target=g.target, start_date=g.start_date, end_date=g.end_date, is_active=g.is_active)
