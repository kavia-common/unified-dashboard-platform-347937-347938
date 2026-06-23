from __future__ import annotations

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.dialects import DialectCITEXT, DialectJSONB, DialectUUID, uuid_pk_column


class AppUser(Base):
    __tablename__ = "app_user"

    id: Mapped[str] = uuid_pk_column()
    firebase_uid: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    email: Mapped[str | None] = mapped_column(DialectCITEXT(), nullable=True)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    profile: Mapped["UserProfile"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profile"

    user_id: Mapped[str] = mapped_column(
        DialectUUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="CASCADE"),
        primary_key=True,
    )

    birthdate: Mapped[object | None] = mapped_column(Date, nullable=True)
    sex: Mapped[str | None] = mapped_column(Text, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(nullable=True)
    timezone: Mapped[str | None] = mapped_column(Text, nullable=True)
    locale: Mapped[str | None] = mapped_column(Text, nullable=True)

    fitness_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    injuries: Mapped[str | None] = mapped_column(Text, nullable=True)
    equipment: Mapped[dict] = mapped_column(DialectJSONB(), nullable=False, server_default="[]")

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: Mapped["AppUser"] = relationship(back_populates="profile")
