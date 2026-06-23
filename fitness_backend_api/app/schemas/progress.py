from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class BodyMetricCreateRequest(BaseModel):
    measured_at: datetime | None = None
    weight_kg: float | None = Field(None, description="Body weight in kg.")
    body_fat_pct: float | None = Field(None, description="0-100")
    measurements: dict = Field(default_factory=dict, description="Circumferences and other metrics.")
    notes: str | None = None


class BodyMetricUpdateRequest(BaseModel):
    """Patch/update a body metric entry (all fields optional)."""

    measured_at: datetime | None = None
    weight_kg: float | None = Field(None, description="Body weight in kg.")
    body_fat_pct: float | None = Field(None, description="0-100")
    measurements: dict | None = Field(None, description="Circumferences and other metrics.")
    notes: str | None = None


class BodyMetricResponse(BaseModel):
    id: str
    measured_at: datetime
    weight_kg: float | None
    body_fat_pct: float | None
    measurements: dict


class PersonalRecordCreateRequest(BaseModel):
    exercise_id: str | None = None
    pr_type: str = Field(..., description="1rm | max_reps | max_volume | best_time | best_distance | other")
    value: dict = Field(default_factory=dict)
    achieved_at: datetime | None = None
    notes: str | None = None


class PersonalRecordUpdateRequest(BaseModel):
    """Patch/update a PR entry (all fields optional)."""

    exercise_id: str | None = None
    pr_type: str | None = Field(None, description="1rm | max_reps | max_volume | best_time | best_distance | other")
    value: dict | None = None
    achieved_at: datetime | None = None
    notes: str | None = None


class PersonalRecordResponse(BaseModel):
    id: str
    pr_type: str
    value: dict
    achieved_at: datetime


class ProgressPhotoCreateRequest(BaseModel):
    """
    Create a progress photo metadata row.

    This backend does not upload binary image blobs; it stores metadata + a pointer
    (object_key/url). A future storage integration can populate object_key/url.
    """

    taken_at: datetime | None = None
    storage_provider: str = Field("local", description="Storage provider identifier (e.g. local/s3/gcs).")
    object_key: str = Field(..., description="Object key/path in the storage provider.")
    url: str | None = Field(None, description="Optional public URL.")
    caption: str | None = None

    # Migration 002 fields (optional)
    meta: dict = Field(default_factory=dict, description="Additional photo metadata.")
    mime_type: str | None = None
    file_size_bytes: int | None = Field(None, ge=0)
    width_px: int | None = Field(None, gt=0)
    height_px: int | None = Field(None, gt=0)


class ProgressPhotoResponse(BaseModel):
    id: str
    taken_at: datetime
    storage_provider: str
    object_key: str
    url: str | None
    caption: str | None

    meta: dict = Field(default_factory=dict)
    mime_type: str | None
    file_size_bytes: int | None
    width_px: int | None
    height_px: int | None
