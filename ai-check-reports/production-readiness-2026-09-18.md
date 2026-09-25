# Axis Production Readiness Report

Date: 2026-09-18
Loop limit: 3 iterations per phase
Iterations used: 1

## Phase 1 — Security audit

### Reviewed files

- `node-backend/src/models/User.js`
- `node-backend/src/security/jwt.js`
- `node-backend/src/controllers/authController.js`
- `node-backend/src/middlewares/authMiddleware.js`
- `node-backend/src/app.js`
- `node-backend/src/server.js`
- `js/auth.js`

### Confirmed controls

- Passwords use Argon2id with 64 MB memory, three iterations, and four lanes.
- Refresh tokens use SHA-256 hashes and `crypto.timingSafeEqual`.
- Refresh tokens include a random `jti`.
- Refresh rotation uses an atomic compare-and-swap update.
- Reuse detection clears the stored refresh hash and cookie.
- Local cookies use `HttpOnly` and `SameSite=Strict`.
- Production cookies use `HttpOnly`, `SameSite=None`, and `Secure`.
- Production requires two JWT secrets with at least 32 characters.
- NoSQL sanitization and Helmet are enabled.
- Local `.env` files are ignored by Git.

## Phase 2 — API integration

`js/auth.js` now accepts `window.AXIS_API_BASE` as an explicit runtime
override. Existing FastAPI routes remain the default:

- `/api/v1/auth`
- `/api/v1/account`
- `/api/v1`

The Node service currently exposes authentication at `/api/auth` and does not
replace the FastAPI profile, dashboard, or account API.

## Phase 3 — Cloud and DevOps

### Render

`render.yaml` defines:

- Node runtime
- `node-backend` root directory
- `npm ci` build
- `npm start` launch
- `/health` health check
- generated JWT secrets
- dashboard-managed `MONGODB_URI` and `FRONTEND_ORIGIN`

### MongoDB Atlas

`node-backend/DEPLOYMENT.md` documents the `mongodb+srv://` connection format.
The Node service uses:

- `maxPoolSize: 10`
- `minPoolSize: 2`
- `serverSelectionTimeoutMS: 10000`
- `connectTimeoutMS: 10000`
- `socketTimeoutMS: 45000`

### Vercel

The existing `vercel.json` keeps the static frontend and FastAPI rewrites,
including `/health` and `/api/v1/*`.

## Phase 4 — Validation

- Node syntax check: passed.
- Node dependency audit: 0 vulnerabilities.
- Frontend JavaScript syntax: passed.
- TypeScript build: passed.
- FastAPI tests: 12 passed.
- Deployment manifest checks: passed.
- `git diff --check`: passed.
- No screenshots were available under `ai-check-reports/`; visual pixel-level QA
  requires screenshots from desktop and mobile browsers.

## Manual production steps

1. Create a MongoDB Atlas database user and restricted network access.
2. Create a Render service from `render.yaml`.
3. Set `MONGODB_URI` and the exact HTTPS `FRONTEND_ORIGIN` in Render.
4. Deploy the frontend separately to Vercel.
5. Set `window.AXIS_API_BASE` to the FastAPI production URL if it is not
   served from the same origin.
6. Start MongoDB and the Node service, then run `npm run test:security`.

No production deployment or secret rotation was performed automatically.
