from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import AppUser, UserProfile


def get_user_by_id(db: Session, user_id: str) -> AppUser | None:
    return db.execute(select(AppUser).where(AppUser.id == user_id)).scalar_one_or_none()


def get_profile(db: Session, user_id: str) -> UserProfile | None:
    return db.execute(select(UserProfile).where(UserProfile.user_id == user_id)).scalar_one_or_none()


def upsert_profile(db: Session, user_id: str, data: dict) -> UserProfile:
    profile = get_profile(db, user_id)
    if profile is None:
        profile = UserProfile(user_id=user_id, **data)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    for k, v in data.items():
        setattr(profile, k, v)
    db.commit()
    db.refresh(profile)
    return profile
