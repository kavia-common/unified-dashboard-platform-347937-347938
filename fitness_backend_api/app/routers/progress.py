from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.deps import get_db
from app.models.fitness import BodyMetric, PersonalRecord
from app.models.user import AppUser
from app.schemas.progress import (
    BodyMetricCreateRequest,
    BodyMetricResponse,
    PersonalRecordCreateRequest,
    PersonalRecordResponse,
)

router = APIRouter(prefix="/api/progress", tags=["Progress"])


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
