from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import (
    admin_content,
    analytics,
    exercise_library,
    goals,
    health,
    notifications,
    onboarding,
    plans,
    progress,
    share,
    workout_logging,
)


openapi_tags = [
    {"name": "Health", "description": "Service health and operational endpoints."},
    {"name": "Onboarding", "description": "User onboarding and profile management."},
    {"name": "Goals", "description": "Goal setting and goal history."},
    {"name": "Plans", "description": "Workout plans and scheduled sessions."},
    {"name": "Exercise Library", "description": "Exercise catalog and workout templates."},
    {"name": "Workout Logging", "description": "Workout logs, exercises, and sets."},
    {"name": "Progress", "description": "Body metrics, progress photos, and personal records (PRs)."},
    {"name": "Analytics", "description": "Analytics endpoints for dashboards."},
    {"name": "Notifications", "description": "Reminders and notification scheduling."},
    {"name": "Social Sharing", "description": "Share artifacts for workouts/progress."},
    {"name": "Admin", "description": "Admin-only content management (exercises/templates/content)."},
]


app = FastAPI(
    title="Fitness Dashboard Backend API",
    description=(
        "FastAPI backend for the fitness dashboard app.\n\n"
        "Authentication: Provide a Firebase ID token via `Authorization: Bearer <token>`.\n"
        "Admin authorization: Requires Firebase custom claim `admin: true` or DB flag `app_user.is_admin`.\n"
    ),
    version="0.1.0",
    openapi_tags=openapi_tags,
)

# CORS
cors_origins = [o.strip() for o in (settings.backend_cors_origins or "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    # Prefer explicit origins (especially when allow_credentials=True). If not configured,
    # default to common local dev frontend origins.
    allow_origins=cors_origins or ["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health.router)
app.include_router(onboarding.router)
app.include_router(goals.router)
app.include_router(plans.router)
app.include_router(exercise_library.router)
app.include_router(workout_logging.router)
app.include_router(progress.router)
app.include_router(analytics.router)
app.include_router(notifications.router)
app.include_router(share.router)
app.include_router(admin_content.router)
app.include_router(admin_content.public_router)
