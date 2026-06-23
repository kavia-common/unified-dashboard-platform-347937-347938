from __future__ import annotations

import json
from functools import lru_cache

import firebase_admin
from firebase_admin import auth as fb_auth
from firebase_admin import credentials
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.deps import get_db
from app.models.user import AppUser


bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _init_firebase() -> None:
    """Initialize Firebase Admin SDK once per process."""
    if firebase_admin._apps:
        return

    cred = None
    if settings.firebase_service_account_json:
        cred = credentials.Certificate(json.loads(settings.firebase_service_account_json))
    elif settings.firebase_service_account_json_path:
        cred = credentials.Certificate(settings.firebase_service_account_json_path)
    else:
        # No credentials configured: we fail fast when verifying tokens.
        return

    firebase_admin.initialize_app(cred)


def _raise_unauthorized(detail: str = "Unauthorized") -> None:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _raise_forbidden(detail: str = "Forbidden") -> None:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


# PUBLIC_INTERFACE
def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AppUser:
    """Resolve the current authenticated user from a Firebase ID token."""
    if creds is None or not creds.credentials:
        _raise_unauthorized("Missing Bearer token")

    _init_firebase()
    if not settings.firebase_service_account_json and not settings.firebase_service_account_json_path:
        _raise_unauthorized("Firebase Admin credentials not configured on backend")

    try:
        decoded = fb_auth.verify_id_token(creds.credentials)
    except Exception:
        _raise_unauthorized("Invalid token")

    firebase_uid = decoded.get("uid")
    if not firebase_uid:
        _raise_unauthorized("Token missing uid")

    email = decoded.get("email")
    name = decoded.get("name")
    picture = decoded.get("picture")

    # Upsert AppUser
    existing = db.execute(select(AppUser).where(AppUser.firebase_uid == firebase_uid)).scalar_one_or_none()
    if existing is None:
        user = AppUser(firebase_uid=firebase_uid, email=email, display_name=name, photo_url=picture)
        # Admin via custom claim (optional)
        user.is_admin = bool(decoded.get("admin", False))
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    # Keep info fresh
    if email and existing.email != email:
        existing.email = email
    if name and existing.display_name != name:
        existing.display_name = name
    if picture and existing.photo_url != picture:
        existing.photo_url = picture

    # If Firebase claim grants admin, persist it
    if decoded.get("admin") is True and existing.is_admin is False:
        existing.is_admin = True

    if existing.is_disabled:
        _raise_forbidden("Account disabled")

    db.commit()
    db.refresh(existing)
    return existing


# PUBLIC_INTERFACE
def require_admin(user: AppUser = Depends(get_current_user)) -> AppUser:
    """Require an admin user (RBAC gate)."""
    if not user.is_admin:
        _raise_forbidden("Admin access required")
    return user
