from pydantic import BaseModel, Field


class OkResponse(BaseModel):
    ok: bool = Field(True, description="Whether the operation succeeded.")
