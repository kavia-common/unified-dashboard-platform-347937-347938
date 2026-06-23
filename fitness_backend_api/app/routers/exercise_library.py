from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_admin
from app.db.deps import get_db
from app.models.fitness import Exercise, WorkoutTemplate
from app.models.user import AppUser
from app.schemas.exercises import (
    ExerciseCreateRequest,
    ExerciseResponse,
    TemplateCreateRequest,
    TemplateResponse,
)

router = APIRouter(prefix="/api/exercises", tags=["Exercise Library"])


@router.get(
    "",
    response_model=list[ExerciseResponse],
    summary="List exercises",
    description="List public exercises plus the current user's own exercises (excluding archived/deleted).",
    operation_id="list_exercises",
)
def list_exercises(
    q: str | None = Query(None, description="Optional search query (matches name)."),
    user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ExerciseResponse]:
    """List exercises visible to the current user."""
    stmt = (
        select(Exercise)
        .where(Exercise.deleted_at.is_(None))
        .where(Exercise.is_archived.is_(False))
        .where(or_(Exercise.is_public.is_(True), Exercise.created_by == user.id))
        .order_by(Exercise.name.asc())
    )
    if q:
        stmt = stmt.where(Exercise.name.ilike(f"%{q}%"))
    rows = db.execute(stmt).scalars()
    return [
        ExerciseResponse(
            id=str(e.id),
            name=e.name,
            description=e.description,
            primary_muscle_group=e.primary_muscle_group,
            equipment=list(e.equipment or []),
            is_public=e.is_public,
            is_archived=e.is_archived,
        )
        for e in rows
    ]


# Admin endpoints (exercise CRUD)
@router.post(
    "",
    response_model=ExerciseResponse,
    summary="Create exercise (admin)",
    description="Create a global/public exercise. Admin only.",
    operation_id="admin_create_exercise",
    tags=["Admin"],
)
def admin_create_exercise(
    req: ExerciseCreateRequest,
    admin: AppUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ExerciseResponse:
    """Admin: create a public exercise entry."""
    e = Exercise(
        created_by=None,
        name=req.name,
        description=req.description,
        primary_muscle_group=req.primary_muscle_group,
        secondary_muscle_groups=req.secondary_muscle_groups,
        equipment=req.equipment,
        movement_pattern=req.movement_pattern,
        difficulty=req.difficulty,
        instructions=req.instructions,
        media=req.media,
        is_public=req.is_public,
        is_archived=False,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return ExerciseResponse(
        id=str(e.id),
        name=e.name,
        description=e.description,
        primary_muscle_group=e.primary_muscle_group,
        equipment=list(e.equipment or []),
        is_public=e.is_public,
        is_archived=e.is_archived,
    )


# Templates
tpl_router = APIRouter(prefix="/api/templates", tags=["Exercise Library"])


@tpl_router.get(
    "",
    response_model=list[TemplateResponse],
    summary="List workout templates",
    description="List public templates plus the current user's own templates (excluding archived/deleted).",
    operation_id="list_templates",
)
def list_templates(user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[TemplateResponse]:
    """List templates visible to current user."""
    rows = db.execute(
        select(WorkoutTemplate)
        .where(WorkoutTemplate.deleted_at.is_(None))
        .where(WorkoutTemplate.is_archived.is_(False))
        .where(or_(WorkoutTemplate.is_public.is_(True), WorkoutTemplate.owner_user_id == user.id))
        .order_by(WorkoutTemplate.created_at.desc())
    ).scalars()
    return [
        TemplateResponse(
            id=str(t.id),
            title=t.title,
            description=t.description,
            tags=list(t.tags or []),
            is_public=t.is_public,
            is_archived=t.is_archived,
        )
        for t in rows
    ]


@tpl_router.post(
    "",
    response_model=TemplateResponse,
    summary="Create workout template (admin)",
    description="Create a global workout template. Admin only.",
    operation_id="admin_create_template",
    tags=["Admin"],
)
def admin_create_template(
    req: TemplateCreateRequest,
    admin: AppUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TemplateResponse:
    """Admin: create a global workout template."""
    t = WorkoutTemplate(
        owner_user_id=None,
        title=req.title,
        description=req.description,
        tags=req.tags,
        is_public=req.is_public,
        is_archived=False,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return TemplateResponse(
        id=str(t.id),
        title=t.title,
        description=t.description,
        tags=list(t.tags or []),
        is_public=t.is_public,
        is_archived=t.is_archived,
    )


router.include_router(tpl_router)
