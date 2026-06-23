from datetime import datetime
from pydantic import BaseModel, Field


class AdminContentCreateRequest(BaseModel):
    content_type: str = Field(..., description="article | tip | program | announcement")
    title: str = Field(..., description="Title.")
    slug: str = Field(..., description="Unique slug.")
    summary: str | None = None
    body_markdown: str = Field(..., description="Markdown body.")
    tags: list[str] = Field(default_factory=list)
    is_published: bool = False
    published_at: datetime | None = None


class AdminContentResponse(BaseModel):
    id: str
    content_type: str
    title: str
    slug: str
    summary: str | None
    body_markdown: str
    tags: list[str]
    is_published: bool
    published_at: datetime | None
