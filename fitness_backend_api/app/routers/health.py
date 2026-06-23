from fastapi import APIRouter

from app.schemas.common import OkResponse

router = APIRouter(prefix="/api", tags=["Health"])


@router.get(
    "/health",
    response_model=OkResponse,
    summary="Health check",
    description="Lightweight health check endpoint for uptime monitoring.",
    operation_id="health_check",
)
def health_check() -> OkResponse:
    """Return ok=true if the service is running."""
    return OkResponse(ok=True)


@router.get(
    "/docs/help",
    summary="API usage help",
    description="Quick notes on using Firebase Bearer tokens with the API.",
    operation_id="docs_help",
    tags=["Health"],
)
def docs_help() -> dict:
    """Provide basic documentation notes for using this API."""
    return {
        "auth": {
            "type": "firebase_id_token",
            "header": "Authorization: Bearer <token>",
            "notes": "Tokens are verified server-side via Firebase Admin SDK.",
        },
        "admin": {
            "requirements": ["Firebase custom claim admin=true OR DB app_user.is_admin=true"],
        },
    }
