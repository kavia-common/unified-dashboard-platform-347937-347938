# fitness_backend_api

FastAPI backend for the fitness dashboard app.

## Setup

1) Create a virtualenv and install deps:

```bash
pip install -r requirements.txt
```

2) Configure environment variables (see `.env.example`):

- `DATABASE_URL`
- `FIREBASE_SERVICE_ACCOUNT_JSON_PATH` or `FIREBASE_SERVICE_ACCOUNT_JSON`
- `BACKEND_CORS_ORIGINS`

3) Run:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Auth

All protected endpoints require:

`Authorization: Bearer <Firebase ID token>`

Admin endpoints require either:
- Firebase custom claim `admin: true`, OR
- DB user flag `app_user.is_admin = true`.
