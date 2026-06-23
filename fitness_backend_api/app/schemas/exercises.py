from pydantic import BaseModel, Field


class ExerciseCreateRequest(BaseModel):
    name: str = Field(..., description="Exercise name.")
    description: str | None = None
    primary_muscle_group: str | None = None
    secondary_muscle_groups: list[str] = Field(default_factory=list)
    equipment: list[str] = Field(default_factory=list)
    movement_pattern: str | None = None
    difficulty: str | None = Field(None, description="beginner | intermediate | advanced")
    instructions: list = Field(default_factory=list, description="List of instruction steps.")
    media: dict = Field(default_factory=dict, description="Media URLs and related metadata.")
    is_public: bool = True


class ExerciseResponse(BaseModel):
    id: str
    name: str
    description: str | None
    primary_muscle_group: str | None
    equipment: list[str]
    is_public: bool
    is_archived: bool


class TemplateCreateRequest(BaseModel):
    title: str = Field(..., description="Template title.")
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    is_public: bool = False


class TemplateResponse(BaseModel):
    id: str
    title: str
    description: str | None
    tags: list[str]
    is_public: bool
    is_archived: bool
