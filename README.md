# AXIS — Academic & X-Career Intelligent System

[![Frontend](https://img.shields.io/badge/frontend-HTML%20%2F%20CSS%20%2F%20JavaScript-E34F26)](./)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688)](./backend/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC)](./backend/tests/)

AXIS is an open-source career-orientation and development platform for high-school students. It combines an academic and personal profile, Holland RIASEC interests, language certificates, achievement and extracurricular data, and a quantitative career-matching engine to help users compare 24 career domains and identify practical development gaps.

> **Project status:** local frontend/backend integration is working. Production hardening, operational controls, and additional API coverage are still required before treating the service as production-ready.

## Overview

The application currently provides:

- A responsive static website with home, profile, assessment, development, career library, career detail, portfolio, and CV Builder pages.
- Authenticated profile, goals, roadmap, assessments, avatars, and private PDF document storage through the FastAPI backend.
- A dashboard that evaluates five AXIS dimensions (`S1`–`S5`), ranks the career catalog, and presents match and gap-risk results.
- Holland RIASEC-based interest signals and subject-aware career metadata.
- A standalone CV Builder editor with local draft persistence and browser print-to-PDF.
- An optional backend AI roadmap endpoint powered by Groq. The API key remains server-side and is never placed in frontend code.

AXIS is decision support, not an admissions, aptitude, or employment guarantee. Recommendations should be reviewed with educators and current, authoritative career information.

## Architecture

AXIS is intentionally split into a framework-free static client and a Python API:

```text
FuturePath/
├── index.html, pages/          Static HTML screens
├── css/global.css              Shared theme, layout, responsive styles
├── js/                         Browser modules and API integration
│   ├── app.js                  Shared frontend data/UI behavior
│   ├── auth.js                 FastAPI auth, account data, HttpOnly-cookie session
│   └── dashboard.js             AXIS dashboard presentation and evaluation flow
├── assets/                     Images and illustrations
├── src/                        Small React/TypeScript icon components
├── package.json                TypeScript type-check/build and test shortcuts
└── backend/
    ├── app/main.py             FastAPI application and error/CORS middleware
    ├── app/api/routes/         Auth, profile, learning, data, AI, and AXIS routes
    ├── app/services/           Matching, calculation, scheduling, and AI services
    ├── app/models/              SQLAlchemy models
    ├── alembic/                 Database migrations (current head: 0009)
    └── tests/                   Focused pytest coverage for matching and S2
```

The frontend is not a bundled SPA: pages are served as static files and call the API with `fetch`. During local development, serve the frontend on a different origin (for example port `5500`) and run FastAPI on port `8000`. The browser sends credentialed requests; authentication tokens are held in an HttpOnly cookie rather than readable JavaScript storage. The legacy `server.py` is only a small Flask contact-form/static proxy for demos and is not the application backend.

### API surface

The FastAPI service exposes health checks at `/health` and `/api/v1/health`. The main resource groups are:

| Route | Purpose |
| --- | --- |
| `/api/v1/auth/*` | Register, login, logout, current user, and avatar operations |
| `/api/v1/profile` | Read and update the authenticated profile |
| `/api/v1/goals` | Manage user-owned goals |
| `/api/v1/roadmap` | Read or replace roadmap steps |
| `/api/v1/assessments` | Read and create assessment results |
| `/api/v1/axis/benchmarks` | Return the shared 24-domain AXIS catalog |
| `/api/v1/axis/evaluate` | Evaluate `S1`–`S5`, persist competency data, and return matches |
| `/api/v1/account/documents` | Store, list, and stream private PDF documents |
| `/api/v1/ai/roadmap` | Generate and persist a seven-day Groq roadmap when configured |

All account resources are scoped to the authenticated user. API errors use a consistent envelope such as `{"error":{"code":"validation_error","message":"Request validation failed"}}`.

## Mathematical engine

The calculation primitives live in [`backend/app/services/calculation_engine.py`](./backend/app/services/calculation_engine.py), independently of FastAPI and SQLAlchemy. Career-specific feature extraction and the 24-domain catalog live in [`backend/app/services/career_matching.py`](./backend/app/services/career_matching.py).

### Hybrid AHP-SAW-ROC

For each career benchmark, AXIS:

1. Normalizes each input against its minimum, maximum, target, and benefit/cost direction using bounded min-max normalization.
2. Computes an AHP priority vector from a positive square pairwise-comparison matrix using a geometric-mean approximation.
3. Calculates Saaty consistency ratio (`CR`) and accepts AHP weights only when `CR ≤ 0.10`.
4. Computes Rank-Order Centroid (ROC) weights from the benchmark priority order. With five criteria, the default descending ROC weights are approximately `0.4567, 0.2567, 0.1567, 0.0900, 0.0400`.
5. Falls back to ROC when AHP is absent or inconsistent, then blends the selected AHP/ROC vector with ROC using the configurable `ahp_blend` (default `0.5`).
6. Produces a weighted SAW match percentage and a weighted root-mean-square gap-risk percentage. Scores are bounded to the `0–100` range by the API contract.

The five dimensions are:

- `S1` — academic performance and relevant subjects
- `S2` — foreign-language capability
- `S3` — achievements
- `S4` — Holland RIASEC interests/personality signals
- `S5` — extracurricular activity and impact

### S2 language-certificate conversion

`S2` converts supported language evidence to the common AXIS `0–10` scale before matching. The implementation recognizes IELTS/TOEIC, TOEFL, HSK, JLPT, DELF/DALF, TOPIK, and Goethe/TestDaF patterns, clamps out-of-range values, ignores expired certificates, and uses the strongest available result. Multiple strong certificates may receive a small capped bonus. Examples covered by the test suite include IELTS 6.5 → `9.0`, JLPT N2 → `9.0`, and HSK 5 → `9.0`.

## Setup

### Prerequisites

- Python 3.10 or newer
- Node.js and npm (only needed for the TypeScript icon build check)
- A browser
- PostgreSQL for deployment; SQLite is the default for local development

### Backend (FastAPI)

From the project directory:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Set JWT_SECRET_KEY and adjust DATABASE_URL/CORS_ORIGINS in .env.
alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
```

The local default is `sqlite:///./dev.db`. For deployment, set `DATABASE_URL` to a PostgreSQL URL such as `postgresql+psycopg2://user:password@host:5432/axis`. Set a stable, high-entropy `JWT_SECRET_KEY`; set `COOKIE_SECURE=true` when serving over HTTPS. `GROQ_API_KEY` is optional and enables the AI roadmap route.

### Frontend (static server)

In a second terminal, from the project directory:

```powershell
python -m http.server 5500
```

Open <http://127.0.0.1:5500/>. The frontend's local API configuration targets FastAPI at port `8000`; ensure the frontend origin is included in `backend/.env` under `CORS_ORIGINS`. Do not use `file://` for authenticated or cross-origin flows.

For a quick, unauthenticated static preview, the bundled Flask demo can also be run with `python server.py` and opened at <http://127.0.0.1:5000/>. It is not a substitute for FastAPI and its contact endpoint has intentionally permissive demo CORS; do not deploy it as-is.

## Development and testing

Install the frontend dependencies when working on the TypeScript icon components:

```powershell
npm install
npm run build
```

Run the focused backend tests from the project root:

```powershell
npm test
```

The test shortcut runs `backend/tests/test_career_matching.py` through pytest. To run both backend test modules directly:

```powershell
cd backend
python -m pytest tests -q
```

The current suite covers career-match score bounds and representative S2 conversions, including expired certificates and clamping. API integration coverage should be expanded as the backend evolves.

## Deployment notes

- Serve the static frontend from a static host (Nginx, GitHub Pages, object storage/CDN, or an equivalent HTTP server) and deploy FastAPI separately behind an HTTPS reverse proxy or managed ASGI service.
- Configure the frontend/API origin relationship deliberately. Use explicit origins in `CORS_ORIGINS`; never use `*` with credentialed cookies.
- Use PostgreSQL and run `alembic upgrade head` as a release step. Do not use the checked-in local SQLite database for production.
- Set `JWT_SECRET_KEY`, `COOKIE_SECURE=true`, and production `ENVIRONMENT` through the platform's secret/configuration manager. Never commit `.env` or API keys.
- Put the API behind TLS, restrict database/network access, and add backups, logging, rate limiting, monitoring, and a process manager/container strategy before public launch.
- Keep uploaded avatars and PDF documents private. The API validates image uploads and ownership, but production deployments still need durable private storage and operational retention limits.
- The Groq integration is optional. If enabled, protect the key server-side and add usage/rate controls before exposing the AI route publicly.
- GitHub Pages can host the static pages only; it cannot run FastAPI, database migrations, authentication, or `server.py`.

## Documentation note

[`README_SUMMARY.md`](./README_SUMMARY.md) is retained as a supplementary UI/design QA handoff. It contains historical notes about the frontend and may mention earlier prototype behavior (for example, localStorage-only data or the absence of tests). This README and the source files are the authoritative description of the current integrated static frontend + FastAPI architecture.

## Contributing

Issues and pull requests are welcome. Please keep changes focused, add or update tests for calculation or API behavior, avoid committing secrets or runtime data, and document any changes to the scoring model or benchmark catalog. Before opening a pull request, run `npm run build` and `npm test`.

## License

No license file is currently included. Until a license is added by the maintainers, reuse and redistribution rights should not be assumed.