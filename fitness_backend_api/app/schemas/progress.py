from datetime import datetime
from pydantic import BaseModel, Field


class BodyMetricCreateRequest(BaseModel):
    measured_at: datetime | None = None
    weight_kg: float | None = Field(None, description="Body weight in kg.")
    body_fat_pct: float | None = Field(None, description="0-100")
    measurements: dict = Field(default_factory=dict, description="Circumferences and other metrics.")
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


class PersonalRecordResponse(BaseModel):
    id: str
    pr_type: str
    value: dict
    achieved_at: datetime
