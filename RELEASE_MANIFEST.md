# FuturePath — Release Update Manifest

**Updated:** 2026-10-10
**Branch:** `release/futurepath-predeploy`
**Base commit:** `10394e2` (remote branch HEAD)
**Candidate state:** committed locally; not pushed or deployed.

## Update contents

### Runtime changes

- `backend/app/api/routes/tasks.py`, `backend/app/services/ai.py`, and `backend/app/services/schedule.py`: validate and save personalized three-day plans as calendar tasks, preserve task durations/resources, and enforce daily capacity.
- `backend/app/core/time.py`, `backend/app/services/task_planner.py`, and task routes: use Vietnam local dates for task generation and overdue reconciliation.
- `js/calendar.js`, `pages/calendar.html`, and `pages/development.html`: connect task CRUD/status and generated plans to the calendar; render the empty month even before sign-in/API access.
- `js/career-images.js`, `pages/careers.html`, and `pages/career-detail.html`: add career imagery and related discovery details.
- `pages/profile.html`, `js/app.js`, `js/cv-builder-editor.js`, `css/global.css`, and `css/cv-builder-editor.css`: improve profile/certificate fields, preserve edits during profile hydration, and render TOEIC component scores in CVs.
- `js/auth.js`: normalize the configured auth API base when building account endpoints.
- `components/header.html`: restore the calendar navigation item.
- `pages/about.html`: update the related page content.

### Verification and local-only changes

- `backend/tests/test_task_planner.py` and `tests/frontend-smoke.mjs` cover task duration/resource handling, malformed AI plans, Vietnam date boundaries, current roadmap UI, and the guest calendar state.
- `dev_proxy.py` adds local PATCH proxy support; it is not needed in the Vercel runtime package.
- The changed workbook `students_anonymized_30.xlsx` is analysis/demo data, not application runtime data. Its aggregate formulas were replaced with values and three sheets were added. Exclude it from this release and do not upload it to Vercel.
- The untracked `demo/` folder contains demo recordings, screenshots, browser state, and test artifacts. Exclude it from Git release contents and Vercel deployment.
- The parent workspace has additional unrelated files outside the `FuturePath` Git repository; they are not part of this candidate.

The Vercel allowlist in `.vercelignore` includes the new `js/career-images.js` and backend time helper through their parent folders, while excluding workbooks, tests, QA material, and the demo folder.

## Checks run

| Check | Result |
|---|---|
| Backend full pytest suite | 101 passed |
| Focused task planner suite | 12 passed |
| Frontend smoke | 31 passed |
| TypeScript build | Passed |
| Root career-matching test command | 30 passed |
| Node auth-service syntax check | Passed |
| Browser routes | Main, about, calendar, career detail, careers, development, profile, assessment, and RIASEC loaded locally; calendar navigation and guest month rendering verified |
| Playwright UI/UX suite | **16/16 passed** on an isolated SQLite database upgraded through Alembic head. All 51 route/view-size checks passed across desktop, tablet, and mobile; 12 axe scans found 0 automated violations. Auth, profile, dashboard, assessment-to-career save, calendar CRUD and AI-unavailable feedback, development, settings, careers, RIASEC draft/submit/retake, and CV editor flows passed. |
| Auth-service security integration | Not run successfully: local auth service at 127.0.0.1:3001 was unavailable |
| Vercel production environment | Added explicit `ENVIRONMENT=production`, `COOKIE_SECURE=true`, and `CORS_ORIGINS=https://axis-career-app.vercel.app`; values are present in the Vercel project without exposing secrets |
| Vercel production build | Passed from a clean export of the staged release files. A direct Windows workspace build hit `EPERM` while copying local `.agents`/`.claude` tooling links. |
| Production health | `https://axis-career-app.vercel.app/health` and `/api/v1/health` returned HTTP 200 before deployment |
| Production database / authenticated flows | Blocked: the Neon AXIS project reports its default `production` branch as archived. Vercel protects `DATABASE_URL`, so its mapping to that branch and Alembic revision could not be confirmed. |
| `git diff --check` | Passed |
| Python dependency check (`pip check`) | Passed |

## Deploy blockers

**Verdict: NOT READY TO DEPLOY.**

1. Confirm which database Vercel production uses and restore/provision an active production database branch. The Neon AXIS account's default `production` branch is archived; the protected Vercel `DATABASE_URL` could not be compared to it.
2. Verify that database's Alembic revision and apply migration `0011_add_user_synthetic_marker` through the approved deployment path if needed.
3. Run authenticated production smoke flows against the active database. Health endpoints alone do not confirm database connectivity.
4. Push the reviewed release commit only after the database target is active; pushing the configured release branch may start Render auto-deploy with migrations.

No production settings, database, migration, deployment, or remote branch were changed. Render configuration has `autoDeploy: true`; pushing a matching branch may trigger its deployment automatically.
