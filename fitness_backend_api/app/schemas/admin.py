from __future__ import annotations

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


class AdminContentUpdateRequest(BaseModel):
    """Patch/update admin content (all fields optional)."""

    content_type: str | None = Field(None, description="article | tip | program | announcement")
    title: str | None = Field(None, description="Title.")
    slug: str | None = Field(None, description="Unique slug.")
    summary: str | None = None
    body_markdown: str | None = Field(None, description="Markdown body.")
    tags: list[str] | None = None
    is_published: bool | None = None
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


class PublicContentFeedItem(BaseModel):
    """Public-facing content entry for the in-app feed (published only)."""

    id: str
    content_type: str
    title: str
    slug: str
    summary: str | None
    tags: list[str] = Field(default_factory=list)
    published_at: datetime | None
