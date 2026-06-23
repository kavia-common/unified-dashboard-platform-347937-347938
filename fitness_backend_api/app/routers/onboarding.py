from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.crud.users import get_profile, upsert_profile
from app.db.deps import get_db
from app.models.user import AppUser
from app.schemas.onboarding import ProfileResponse, ProfileUpsertRequest

router = APIRouter(prefix="/api", tags=["Onboarding"])


@router.get(
    "/me",
    response_model=ProfileResponse,
    summary="Get current user profile",
    description="Returns the authenticated user plus onboarding/profile fields.",
    operation_id="get_me",
)
def get_me(user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> ProfileResponse:
    """Get the current user's profile and basic identity fields."""
    profile = get_profile(db, str(user.id))
    equipment = []
    if profile is not None and isinstance(profile.equipment, list):
        equipment = profile.equipment
    return ProfileResponse(
        user_id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        photo_url=user.photo_url,
        fitness_level=profile.fitness_level if profile else None,
        equipment=equipment,
        injuries=profile.injuries if profile else None,
        birthdate=profile.birthdate if profile else None,
        sex=profile.sex if profile else None,
        height_cm=float(profile.height_cm) if profile and profile.height_cm is not None else None,
        timezone=profile.timezone if profile else None,
        locale=profile.locale if profile else None,
    )


@router.put(
    "/me",
    response_model=ProfileResponse,
    summary="Upsert current user profile",
    description="Creates or updates onboarding/profile fields for the authenticated user.",
    operation_id="upsert_me",
)
def upsert_me(
    req: ProfileUpsertRequest,
    user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    """Upsert current user's onboarding/profile record."""
    payload = req.model_dump(exclude_unset=True)
    if "equipment" in payload and payload["equipment"] is None:
        payload["equipment"] = []
    profile = upsert_profile(db, str(user.id), payload)
    equipment = profile.equipment if isinstance(profile.equipment, list) else []
    return ProfileResponse(
        user_id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        photo_url=user.photo_url,
        fitness_level=profile.fitness_level,
        equipment=equipment,
        injuries=profile.injuries,
        birthdate=profile.birthdate,
        sex=profile.sex,
        height_cm=float(profile.height_cm) if profile.height_cm is not None else None,
        timezone=profile.timezone,
        locale=profile.locale,
    )
