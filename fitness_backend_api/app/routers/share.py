from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.deps import get_db
from app.models.fitness import BodyMetric, PersonalRecord, ProgressPhoto, ShareArtifact, WorkoutLog
from app.models.user import AppUser
from app.schemas.share import ShareArtifactCreateRequest, ShareArtifactResponse

router = APIRouter(prefix="/api/share", tags=["Social Sharing"])


def _is_expired(a: ShareArtifact) -> bool:
    if a.expires_at is None:
        return False
    now = datetime.now(timezone.utc)
    return a.expires_at < now


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
    description=(
        "Public endpoint to resolve a share artifact by token (if public and not expired). "
        "Includes a best-effort rendered payload when ref_table/ref_id points to known entities."
    ),
    operation_id="get_share_artifact_by_token",
    tags=["Social Sharing"],
)
def get_share_artifact_by_token(share_token: str, db: Session = Depends(get_db)) -> dict:
    """Resolve a public share artifact."""
    a = db.execute(
        select(ShareArtifact).where(ShareArtifact.share_token == share_token).where(ShareArtifact.deleted_at.is_(None))
    ).scalar_one_or_none()
    if a is None or not a.is_public or _is_expired(a):
        raise HTTPException(status_code=404, detail="Not found")

    rendered: dict | None = None
    ref_table = (a.ref_table or "").strip() if a.ref_table else None
    ref_id = str(a.ref_id) if a.ref_id else None

    # Best-effort, safe joins for known share artifact references.
    try:
        if ref_table == "progress_photo" and ref_id:
            p = db.execute(
                select(ProgressPhoto).where(ProgressPhoto.id == ref_id).where(ProgressPhoto.deleted_at.is_(None))
            ).scalar_one_or_none()
            if p is not None:
                rendered = {
                    "type": "progress_photo",
                    "taken_at": p.taken_at,
                    "url": p.url,
                    "caption": p.caption,
                    "storage_provider": p.storage_provider,
                    "object_key": p.object_key,
                }
        elif ref_table == "workout_log" and ref_id:
            w = db.execute(select(WorkoutLog).where(WorkoutLog.id == ref_id).where(WorkoutLog.deleted_at.is_(None))).scalar_one_or_none()
            if w is not None:
                rendered = {
                    "type": "workout_log",
                    "started_at": w.started_at,
                    "ended_at": w.ended_at,
                    "title": w.title,
                    "notes": w.notes,
                    "rpe": w.rpe,
                    "calories_burned": float(w.calories_burned) if w.calories_burned is not None else None,
                }
        elif ref_table == "body_metric" and ref_id:
            m = db.execute(select(BodyMetric).where(BodyMetric.id == ref_id).where(BodyMetric.deleted_at.is_(None))).scalar_one_or_none()
            if m is not None:
                rendered = {
                    "type": "body_metric",
                    "measured_at": m.measured_at,
                    "weight_kg": float(m.weight_kg) if m.weight_kg is not None else None,
                    "body_fat_pct": float(m.body_fat_pct) if m.body_fat_pct is not None else None,
                    "measurements": m.measurements or {},
                }
        elif ref_table == "personal_record" and ref_id:
            pr = db.execute(
                select(PersonalRecord).where(PersonalRecord.id == ref_id).where(PersonalRecord.deleted_at.is_(None))
            ).scalar_one_or_none()
            if pr is not None:
                rendered = {
                    "type": "personal_record",
                    "pr_type": pr.pr_type,
                    "value": pr.value or {},
                    "achieved_at": pr.achieved_at,
                    "notes": pr.notes,
                }
    except Exception:
        # Share is a public endpoint; avoid leaking internal errors.
        rendered = None

    return {
        "artifact_type": a.artifact_type,
        "title": a.title,
        "description": a.description,
        "ref_table": a.ref_table,
        "ref_id": ref_id,
        "created_at": a.created_at,
        "rendered": rendered,
    }
