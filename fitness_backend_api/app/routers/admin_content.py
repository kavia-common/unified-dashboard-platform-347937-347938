from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.db.deps import get_db
from app.models.fitness import AdminContent
from app.models.user import AppUser
from app.schemas.admin import AdminContentCreateRequest, AdminContentResponse

router = APIRouter(prefix="/api/admin/content", tags=["Admin"])


@router.get(
    "",
    response_model=list[AdminContentResponse],
    summary="List admin content",
    description="Admin-only: list content entries (including drafts).",
    operation_id="admin_list_content",
)
def admin_list_content(admin: AppUser = Depends(require_admin), db: Session = Depends(get_db)) -> list[AdminContentResponse]:
    """Admin: list admin content."""
    rows = db.execute(
        select(AdminContent).where(AdminContent.deleted_at.is_(None)).order_by(AdminContent.created_at.desc())
    ).scalars()
    return [
        AdminContentResponse(
            id=str(c.id),
            content_type=c.content_type,
            title=c.title,
            slug=c.slug,
            summary=c.summary,
            body_markdown=c.body_markdown,
            tags=list(c.tags or []),
            is_published=c.is_published,
            published_at=c.published_at,
        )
        for c in rows
    ]


@router.post(
    "",
    response_model=AdminContentResponse,
    summary="Create admin content",
    description="Admin-only: create a content entry (article/tip/program/announcement).",
    operation_id="admin_create_content",
)
def admin_create_content(
    req: AdminContentCreateRequest, admin: AppUser = Depends(require_admin), db: Session = Depends(get_db)
) -> AdminContentResponse:
    """Admin: create admin content."""
    c = AdminContent(
        created_by=admin.id,
        content_type=req.content_type,
        title=req.title,
        slug=req.slug,
        summary=req.summary,
        body_markdown=req.body_markdown,
        tags=req.tags,
        is_published=req.is_published,
        published_at=req.published_at,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return AdminContentResponse(
        id=str(c.id),
        content_type=c.content_type,
        title=c.title,
        slug=c.slug,
        summary=c.summary,
        body_markdown=c.body_markdown,
        tags=list(c.tags or []),
        is_published=c.is_published,
        published_at=c.published_at,
    )
