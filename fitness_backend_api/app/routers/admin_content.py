from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.db.deps import get_db
from app.models.fitness import AdminContent
from app.models.user import AppUser
from app.schemas.admin import (
    AdminContentCreateRequest,
    AdminContentResponse,
    AdminContentUpdateRequest,
    PublicContentFeedItem,
)
from app.schemas.common import OkResponse

router = APIRouter(prefix="/api/admin/content", tags=["Admin"])

public_router = APIRouter(prefix="/api/public", tags=["Social Sharing"])


def _load_content(db: Session, *, content_id: str) -> AdminContent:
    c = db.execute(select(AdminContent).where(AdminContent.id == content_id).where(AdminContent.deleted_at.is_(None))).scalar_one_or_none()
    if c is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return c


@router.get(
    "",
    response_model=list[AdminContentResponse],
    summary="List admin content",
    description="Admin-only: list content entries (including drafts).",
    operation_id="admin_list_content",
)
def admin_list_content(admin: AppUser = Depends(require_admin), db: Session = Depends(get_db)) -> list[AdminContentResponse]:
    """Admin: list admin content."""
    rows = db.execute(select(AdminContent).where(AdminContent.deleted_at.is_(None)).order_by(AdminContent.created_at.desc())).scalars()
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


@router.patch(
    "/{content_id}",
    response_model=AdminContentResponse,
    summary="Update admin content",
    description="Admin-only: patch/update content entry fields.",
    operation_id="admin_update_content",
)
def admin_update_content(
    content_id: str,
    req: AdminContentUpdateRequest,
    admin: AppUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminContentResponse:
    """Admin: update admin content."""
    c = _load_content(db, content_id=content_id)
    payload = req.model_dump(exclude_unset=True)

    for k, v in payload.items():
        if k == "tags" and v is None:
            continue
        setattr(c, k, v)

    # If publishing is toggled on and published_at not provided, set it.
    if payload.get("is_published") is True and (payload.get("published_at") is None) and c.published_at is None:
        c.published_at = datetime.utcnow()

    c.updated_at = func.now()
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


@router.delete(
    "/{content_id}",
    response_model=OkResponse,
    summary="Delete admin content",
    description="Admin-only: soft-delete a content entry.",
    operation_id="admin_delete_content",
)
def admin_delete_content(
    content_id: str,
    admin: AppUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> OkResponse:
    """Admin: soft-delete content."""
    c = _load_content(db, content_id=content_id)
    c.deleted_at = datetime.utcnow()
    c.updated_at = func.now()
    db.commit()
    return OkResponse(ok=True)


@public_router.get(
    "/feed",
    response_model=list[PublicContentFeedItem],
    summary="Public content feed",
    description="List published admin content items (for in-app public feed).",
    operation_id="public_content_feed",
)
def public_content_feed(
    limit: int = Query(20, ge=1, le=100, description="Max items to return."),
    db: Session = Depends(get_db),
) -> list[PublicContentFeedItem]:
    """Public feed of published content."""
    rows = (
        db.execute(
            select(AdminContent)
            .where(AdminContent.deleted_at.is_(None))
            .where(AdminContent.is_published.is_(True))
            .order_by(AdminContent.published_at.desc().nullslast(), AdminContent.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [
        PublicContentFeedItem(
            id=str(c.id),
            content_type=c.content_type,
            title=c.title,
            slug=c.slug,
            summary=c.summary,
            tags=list(c.tags or []),
            published_at=c.published_at,
        )
        for c in rows
    ]
