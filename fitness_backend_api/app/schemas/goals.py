from datetime import date
from pydantic import BaseModel, Field


class GoalCreateRequest(BaseModel):
    goal_type: str = Field(..., description="weight_loss | muscle_gain | endurance | flexibility | general_fitness")
    target: dict = Field(default_factory=dict, description="Flexible structured goal payload.")
    start_date: date | None = Field(None, description="Goal start date (defaults to today).")
    end_date: date | None = Field(None, description="Optional end date.")


class GoalResponse(BaseModel):
    id: str
    goal_type: str
    target: dict
    start_date: date
    end_date: date | None
    is_active: bool
