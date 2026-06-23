from __future__ import annotations

from pydantic import BaseModel, Field


class StartedPlannedSessionResponse(BaseModel):
    """Response returned after starting a planned session (workout log created and prefilled)."""

    workout_log_id: str = Field(..., description="Created workout_log UUID.")
    planned_session_id: str = Field(..., description="Planned workout session UUID.")


class UpdatePlannedSessionStatusRequest(BaseModel):
    """Request to update a planned session status."""

    status: str = Field(..., description="planned | in_progress | completed | skipped | cancelled")


class PlannedSessionStatusResponse(BaseModel):
    """Response for a planned session status update."""

    planned_session_id: str = Field(..., description="Planned workout session UUID.")
    status: str = Field(..., description="New status value.")
