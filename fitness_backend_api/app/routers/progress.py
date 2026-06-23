from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.deps import get_db
from app.models.fitness import BodyMetric, PersonalRecord, ProgressPhoto
from app.models.user import AppUser
from app.schemas.common import OkResponse
from app.schemas.progress import (
    BodyMetricCreateRequest,
    BodyMetricResponse,
    BodyMetricUpdateRequest,
    PersonalRecordCreateRequest,
    PersonalRecordResponse,
    PersonalRecordUpdateRequest,
    ProgressPhotoCreateRequest,
    ProgressPhotoResponse,
)

router = APIRouter(prefix="/api/progress", tags=["Progress"])


def _load_metric_owned(db: Session, *, metric_id: str, user_id: str) -> BodyMetric:
    m = db.execute(
        select(BodyMetric).where(BodyMetric.id == metric_id).where(BodyMetric.user_id == user_id).where(BodyMetric.deleted_at.is_(None))
    ).scalar_one_or_none()
    if m is None:
        raise HTTPException(status_code=404, detail="Metric not found")
    return m


def _load_pr_owned(db: Session, *, pr_id: str, user_id: str) -> PersonalRecord:
    p = db.execute(
        select(PersonalRecord)
        .where(PersonalRecord.id == pr_id)
        .where(PersonalRecord.user_id == user_id)
        .where(PersonalRecord.deleted_at.is_(None))
    ).scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=404, detail="PR not found")
    return p


def _load_photo_owned(db: Session, *, photo_id: str, user_id: str) -> ProgressPhoto:
    p = db.execute(
        select(ProgressPhoto)
        .where(ProgressPhoto.id == photo_id)
        .where(ProgressPhoto.user_id == user_id)
        .where(ProgressPhoto.deleted_at.is_(None))
    ).scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    return p


@router.get(
    "/metrics",
    response_model=list[BodyMetricResponse],
    summary="List body metrics",
    description="List body metrics entries for current user.",
    operation_id="list_body_metrics",
)
def list_body_metrics(user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[BodyMetricResponse]:
    """List body metrics for the current user."""
    rows = db.execute(
        select(BodyMetric).where(BodyMetric.user_id == user.id).where(BodyMetric.deleted_at.is_(None)).order_by(BodyMetric.measured_at.desc())
    ).scalars()
    return [
        BodyMetricResponse(
            id=str(m.id),
            measured_at=m.measured_at,
            weight_kg=float(m.weight_kg) if m.weight_kg is not None else None,
            body_fat_pct=float(m.body_fat_pct) if m.body_fat_pct is not None else None,
            measurements=m.measurements,
        )
        for m in rows
    ]


@router.post(
    "/metrics",
    response_model=BodyMetricResponse,
    summary="Create body metric",
    description="Create a body metric entry.",
    operation_id="create_body_metric",
)
def create_body_metric(req: BodyMetricCreateRequest, user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> BodyMetricResponse:
    """Create a body metric entry for current user."""
    m = BodyMetric(
        user_id=user.id,
        measured_at=req.measured_at,
        weight_kg=req.weight_kg,
        body_fat_pct=req.body_fat_pct,
        measurements=req.measurements,
        notes=req.notes,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return BodyMetricResponse(
        id=str(m.id),
        measured_at=m.measured_at,
        weight_kg=float(m.weight_kg) if m.weight_kg is not None else None,
        body_fat_pct=float(m.body_fat_pct) if m.body_fat_pct is not None else None,
        measurements=m.measurements,
    )


@router.patch(
    "/metrics/{metric_id}",
    response_model=BodyMetricResponse,
    summary="Update body metric",
    description="Patch/update a body metric entry.",
    operation_id="update_body_metric",
)
def update_body_metric(
    metric_id: str,
    req: BodyMetricUpdateRequest,
    user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BodyMetricResponse:
    """Update a body metric entry for the current user."""
    m = _load_metric_owned(db, metric_id=metric_id, user_id=str(user.id))
    payload = req.model_dump(exclude_unset=True)
    for k, v in payload.items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return BodyMetricResponse(
        id=str(m.id),
        measured_at=m.measured_at,
        weight_kg=float(m.weight_kg) if m.weight_kg is not None else None,
        body_fat_pct=float(m.body_fat_pct) if m.body_fat_pct is not None else None,
        measurements=m.measurements,
    )


@router.delete(
    "/metrics/{metric_id}",
    response_model=OkResponse,
    summary="Delete body metric",
    description="Soft-delete a body metric entry.",
    operation_id="delete_body_metric",
)
def delete_body_metric(metric_id: str, user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> OkResponse:
    """Soft-delete a body metric entry."""
    m = _load_metric_owned(db, metric_id=metric_id, user_id=str(user.id))
    m.deleted_at = datetime.utcnow()
    db.commit()
    return OkResponse(ok=True)


@router.get(
    "/prs",
    response_model=list[PersonalRecordResponse],
    summary="List personal records (PRs)",
    description="List PR entries for current user.",
    operation_id="list_personal_records",
)
def list_personal_records(user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[PersonalRecordResponse]:
    """List personal records for the current user."""
    rows = db.execute(
        select(PersonalRecord).where(PersonalRecord.user_id == user.id).where(PersonalRecord.deleted_at.is_(None)).order_by(PersonalRecord.achieved_at.desc())
    ).scalars()
    return [PersonalRecordResponse(id=str(p.id), pr_type=p.pr_type, value=p.value, achieved_at=p.achieved_at) for p in rows]


@router.post(
    "/prs",
    response_model=PersonalRecordResponse,
    summary="Create personal record (PR)",
    description="Create a PR entry for current user.",
    operation_id="create_personal_record",
)
def create_personal_record(
    req: PersonalRecordCreateRequest, user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> PersonalRecordResponse:
    """Create a personal record entry."""
    p = PersonalRecord(
        user_id=user.id,
        exercise_id=req.exercise_id,
        pr_type=req.pr_type,
        value=req.value,
        achieved_at=req.achieved_at,
        notes=req.notes,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return PersonalRecordResponse(id=str(p.id), pr_type=p.pr_type, value=p.value, achieved_at=p.achieved_at)


@router.patch(
    "/prs/{pr_id}",
    response_model=PersonalRecordResponse,
    summary="Update personal record (PR)",
    description="Patch/update a PR entry for current user.",
    operation_id="update_personal_record",
)
def update_personal_record(
    pr_id: str, req: PersonalRecordUpdateRequest, user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> PersonalRecordResponse:
    """Update a PR entry."""
    p = _load_pr_owned(db, pr_id=pr_id, user_id=str(user.id))
    payload = req.model_dump(exclude_unset=True)
    for k, v in payload.items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return PersonalRecordResponse(id=str(p.id), pr_type=p.pr_type, value=p.value, achieved_at=p.achieved_at)


@router.delete(
    "/prs/{pr_id}",
    response_model=OkResponse,
    summary="Delete personal record (PR)",
    description="Soft-delete a PR entry for current user.",
    operation_id="delete_personal_record",
)
def delete_personal_record(pr_id: str, user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> OkResponse:
    """Soft-delete a PR entry."""
    p = _load_pr_owned(db, pr_id=pr_id, user_id=str(user.id))
    p.deleted_at = datetime.utcnow()
    db.commit()
    return OkResponse(ok=True)


@router.get(
    "/photos",
    response_model=list[ProgressPhotoResponse],
    summary="List progress photos",
    description="List progress photos for the current user.",
    operation_id="list_progress_photos",
)
def list_progress_photos(user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ProgressPhotoResponse]:
    """List progress photos for the current user."""
    rows = db.execute(
        select(ProgressPhoto)
        .where(ProgressPhoto.user_id == user.id)
        .where(ProgressPhoto.deleted_at.is_(None))
        .order_by(ProgressPhoto.taken_at.desc())
    ).scalars().all()

    return [
        ProgressPhotoResponse(
            id=str(p.id),
            taken_at=p.taken_at,
            storage_provider=p.storage_provider,
            object_key=p.object_key,
            url=p.url,
            caption=p.caption,
            meta=getattr(p, "meta", {}) or {},
            mime_type=getattr(p, "mime_type", None),
            file_size_bytes=getattr(p, "file_size_bytes", None),
            width_px=getattr(p, "width_px", None),
            height_px=getattr(p, "height_px", None),
        )
        for p in rows
    ]


@router.post(
    "/photos",
    response_model=ProgressPhotoResponse,
    summary="Create progress photo",
    description="Create a progress photo metadata entry for the current user.",
    operation_id="create_progress_photo",
)
def create_progress_photo(
    req: ProgressPhotoCreateRequest, user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> ProgressPhotoResponse:
    """Create a progress photo metadata row."""
    p = ProgressPhoto(
        user_id=user.id,
        taken_at=req.taken_at,
        storage_provider=req.storage_provider,
        object_key=req.object_key,
        url=req.url,
        caption=req.caption,
    )
    # Migration-002 fields (may not exist in ORM yet); set if present.
    for k in ("meta", "mime_type", "file_size_bytes", "width_px", "height_px"):
        if hasattr(p, k):
            setattr(p, k, getattr(req, k))
    db.add(p)
    db.commit()
    db.refresh(p)
    return ProgressPhotoResponse(
        id=str(p.id),
        taken_at=p.taken_at,
        storage_provider=p.storage_provider,
        object_key=p.object_key,
        url=p.url,
        caption=p.caption,
        meta=getattr(p, "meta", {}) or {},
        mime_type=getattr(p, "mime_type", None),
        file_size_bytes=getattr(p, "file_size_bytes", None),
        width_px=getattr(p, "width_px", None),
        height_px=getattr(p, "height_px", None),
    )


@router.delete(
    "/photos/{photo_id}",
    response_model=OkResponse,
    summary="Delete progress photo",
    description="Soft-delete a progress photo metadata entry.",
    operation_id="delete_progress_photo",
)
def delete_progress_photo(photo_id: str, user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> OkResponse:
    """Soft-delete a progress photo metadata row."""
    p = _load_photo_owned(db, photo_id=photo_id, user_id=str(user.id))
    p.deleted_at = datetime.utcnow()
    db.commit()
    return OkResponse(ok=True)
