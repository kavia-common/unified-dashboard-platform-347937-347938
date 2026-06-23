from datetime import datetime
from pydantic import BaseModel, Field


class WorkoutSetIn(BaseModel):
    set_number: int = Field(..., description="1-based set number.")
    reps: int | None = None
    weight_kg: float | None = None
    duration_seconds: int | None = None
    distance_meters: float | None = None
    is_warmup: bool = False
    rpe: int | None = Field(None, description="1-10")
    notes: str | None = None


class WorkoutExerciseIn(BaseModel):
    exercise_id: str = Field(..., description="Exercise UUID.")
    position: int = Field(..., description="0-based position.")
    notes: str | None = None
    sets: list[WorkoutSetIn] = Field(default_factory=list)


class WorkoutLogCreateRequest(BaseModel):
    planned_session_id: str | None = Field(None, description="Optional planned session reference.")
    started_at: datetime | None = Field(None, description="Start timestamp; defaults to now.")
    ended_at: datetime | None = None
    title: str | None = None
    notes: str | None = None
    rpe: int | None = Field(None, description="Workout-level RPE 1-10.")
    calories_burned: float | None = None
    exercises: list[WorkoutExerciseIn] = Field(default_factory=list)


class WorkoutLogResponse(BaseModel):
    id: str
    started_at: datetime
    ended_at: datetime | None
    title: str | None
    notes: str | None
    rpe: int | None
