from datetime import date
from pydantic import BaseModel, Field


class ProfileUpsertRequest(BaseModel):
    fitness_level: str | None = Field(None, description="beginner | intermediate | advanced")
    equipment: list[str] | None = Field(None, description="List of available equipment strings.")
    injuries: str | None = Field(None, description="Free-form injuries/constraints notes.")
    birthdate: date | None = Field(None, description="Optional birthdate.")
    sex: str | None = Field(None, description="male | female | other | prefer_not_say")
    height_cm: float | None = Field(None, description="Height in centimeters.")
    timezone: str | None = Field(None, description="IANA timezone, e.g. America/Los_Angeles")
    locale: str | None = Field(None, description="Locale, e.g. en-US")


class ProfileResponse(BaseModel):
    user_id: str = Field(..., description="UUID of the app user.")
    email: str | None = Field(None, description="Email from Firebase.")
    display_name: str | None = Field(None, description="Display name from Firebase.")
    photo_url: str | None = Field(None, description="Photo URL from Firebase.")

    fitness_level: str | None = None
    equipment: list[str] = Field(default_factory=list)
    injuries: str | None = None
    birthdate: date | None = None
    sex: str | None = None
    height_cm: float | None = None
    timezone: str | None = None
    locale: str | None = None
