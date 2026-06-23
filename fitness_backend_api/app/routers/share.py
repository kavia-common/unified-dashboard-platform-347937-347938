import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.deps import get_db
from app.models.fitness import ShareArtifact
from app.models.user import AppUser
from app.schemas.share import ShareArtifactCreateRequest, ShareArtifactResponse

router = APIRouter(prefix="/api/share", tags=["Social Sharing"])


@router.post(
    "",
    response_model=ShareArtifactResponse,
    summary="Create share artifact",
    description="Create a shareable artifact reference and returns a share_token for public URLs.",
    operation_id="create_share_artifact",
)
def create_share_artifact(
    req: ShareArtifactCreateRequest, user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> ShareArtifactResponse:
    """Create a share artifact for the user."""
    token = secrets.token_urlsafe(24)
    a = ShareArtifact(
        user_id=user.id,
        artifact_type=req.artifact_type,
        ref_table=req.ref_table,
        ref_id=req.ref_id,
        title=req.title,
        description=req.description,
        share_token=token,
        is_public=req.is_public,
        expires_at=req.expires_at,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return ShareArtifactResponse(
        id=str(a.id),
        artifact_type=a.artifact_type,
        title=a.title,
        description=a.description,
        share_token=a.share_token,
        is_public=a.is_public,
        expires_at=a.expires_at,
    )


@router.get(
    "/{share_token}",
    summary="Resolve share artifact",
    description="Public endpoint to resolve a share artifact by token (if public and not expired).",
    operation_id="get_share_artifact_by_token",
    tags=["Social Sharing"],
)
def get_share_artifact_by_token(share_token: str, db: Session = Depends(get_db)) -> dict:
    """Resolve a public share artifact."""
    a = db.execute(
        select(ShareArtifact).where(ShareArtifact.share_token == share_token).where(ShareArtifact.deleted_at.is_(None))
    ).scalar_one_or_none()
    if a is None or not a.is_public:
        raise HTTPException(status_code=404, detail="Not found")

    if a.expires_at is not None:
        now = datetime.now(timezone.utc)
        if a.expires_at < now:
            raise HTTPException(status_code=404, detail="Not found")

    return {
        "artifact_type": a.artifact_type,
        "title": a.title,
        "description": a.description,
        "ref_table": a.ref_table,
        "ref_id": str(a.ref_id) if a.ref_id else None,
        "created_at": a.created_at,
    }
