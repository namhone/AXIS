# AXIS backend

This directory contains the AXIS FastAPI application, authentication API,
career matching engine, learning planner, and Hybrid AHP-SAW-ROC services.
It uses FastAPI, synchronous SQLAlchemy 2, SQLite for local development,
PostgreSQL for deployment, Alembic, Argon2id
password hashing, and short-lived JWTs stored in an HttpOnly cookie.

## Local setup

From `AXIS\backend`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Set DATABASE_URL and a random JWT_SECRET_KEY in .env.
alembic upgrade head
python -m uvicorn app.main:app --reload
```

SQLite (`sqlite:///./dev.db`) is the local default. Set `DATABASE_URL` to a
PostgreSQL URL in deployment.
Set `GROQ_API_KEY` in `.env` to enable the AI roadmap endpoint. The key is
read only by the backend and is never exposed to the frontend.
Importing `main:app` does not connect to the database; migrations or an API
request do.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness check |
| GET | `/health/ready` | Readiness check backed by the database |
| POST | `/api/v1/auth/register` | Create a user and set the auth cookie |
| POST | `/api/v1/auth/login` | Authenticate and set the auth cookie |
| POST | `/api/v1/auth/logout` | Clear the auth cookie |
| GET | `/api/v1/auth/me` | Return the authenticated user |
| PUT | `/api/v1/auth/avatar` | Upload the current user's JPEG, PNG, or WebP avatar (max 5 MB) |
| GET | `/api/v1/auth/avatar` | Stream the current user's private avatar |
| GET/PUT | `/api/v1/profile` | Read or save profile fields for the current user |
| GET/POST/PUT/DELETE | `/api/v1/goals` | Manage goals owned by the current user |
| GET/PUT | `/api/v1/roadmap` | Read or replace roadmap steps owned by the current user |
| GET/POST | `/api/v1/assessments` | Read or create assessment results owned by the current user |
| POST | `/api/v1/ai/roadmap` | Generate and persist a 7-day personalized roadmap with Groq |
| GET | `/api/v1/axis/benchmarks` | Return the shared 24-industry AXIS catalog |
| POST | `/api/v1/axis/evaluate` | Calculate and persist S1–S5 match results |
| POST | `/api/v1/account/documents` | Store a private PDF document for the current user |
| GET | `/api/v1/account/documents` | List the current user's documents |
| GET | `/api/v1/account/documents/{id}` | Stream one private document owned by the current user |
| GET | `/api/v1/account/documents/{id}/download` | Explicit download alias for a private document |

Authentication cookies are `HttpOnly`, `SameSite=Lax`, and use `Secure` when
`COOKIE_SECURE=true`. CORS accepts only exact origins listed in
`CORS_ORIGINS`; do not use `*` with credentialed requests.
For local `file://` testing only, `null` may be added to `CORS_ORIGINS`; remove
it before deployment and prefer serving the frontend through an HTTP server.

Avatar files are stored on the authenticated user's database row. The API
validates the declared MIME type and image signature, limits uploads to 5 MB,
and never accepts a user ID from the client, so accounts cannot overwrite or
read one another's avatars.

Errors have a consistent JSON shape:

```json
{"error": {"code": "validation_error", "message": "Request validation failed"}}
```

The AI roadmap endpoint is limited per authenticated user (and client address)
using a rolling in-memory window. Defaults are 5 requests per 60 seconds and
can be adjusted with `AI_RATE_LIMIT_REQUESTS` and
`AI_RATE_LIMIT_WINDOW_SECONDS`. A rejected request returns HTTP 429 with
`Retry-After` and `error.code` set to `rate_limited`. The limiter is
process-local; deployments with multiple workers should move the counter to a
shared store.

Each API response includes an `X-Request-ID` header. Production request logs
record only method, path, status, duration, and request ID; cookies, tokens,
request bodies, and query strings are never logged. Use `/health` for liveness
and `/health/ready` for database readiness checks.
