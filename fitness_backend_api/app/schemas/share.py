from datetime import datetime
from pydantic import BaseModel, Field


class ShareArtifactCreateRequest(BaseModel):
    artifact_type: str = Field(..., description="progress_photo | workout_summary | metric_snapshot | pr | other")
    ref_table: str | None = None
    ref_id: str | None = None
    title: str | None = None
    description: str | None = None
    is_public: bool = True
    expires_at: datetime | None = None


class ShareArtifactResponse(BaseModel):
    id: str
    artifact_type: str
    title: str | None
    description: str | None
    share_token: str
    is_public: bool
    expires_at: datetime | None
