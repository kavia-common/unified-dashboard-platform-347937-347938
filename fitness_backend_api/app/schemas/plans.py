from datetime import date
from pydantic import BaseModel, Field


class PlanCreateRequest(BaseModel):
    title: str = Field(..., description="Plan title.")
    description: str | None = Field(None, description="Optional plan description.")
    start_date: date | None = Field(None, description="Plan start date (defaults to today).")
    end_date: date | None = Field(None, description="Optional plan end date.")
    source: str | None = Field("manual", description="manual | generated")
    source_meta: dict = Field(default_factory=dict, description="Generator metadata if source=generated.")


class PlanResponse(BaseModel):
    id: str
    title: str
    description: str | None
    start_date: date
    end_date: date | None
    is_active: bool
    source: str | None
    source_meta: dict


class PlannedSessionCreateRequest(BaseModel):
    scheduled_date: date = Field(..., description="Date of the planned session.")
    title: str | None = Field(None, description="Optional title.")
    notes: str | None = Field(None, description="Optional notes.")
    workout_template_id: str | None = Field(None, description="Optional template id to base session on.")
    status: str | None = Field("planned", description="planned | completed | skipped | cancelled")


class PlannedSessionResponse(BaseModel):
    id: str
    workout_plan_id: str
    scheduled_date: date
    title: str | None
    notes: str | None
    workout_template_id: str | None
    status: str
