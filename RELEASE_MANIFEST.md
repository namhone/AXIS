# FuturePath — Proposed Minimum Safe Release Manifest

Scope: repository `FuturePath`, branch `main`, HEAD
`bb9a8a9e9c3e825e57650475bf4682bc51df7179`.

This is a scope proposal only. It does not stage or commit files, deploy the
application, connect to production, or execute migrations. Preserve all files
outside this manifest; exclusion means “not proposed for this release,” not
“delete.”

## Runtime files

These 27 tracked changes are application behavior or deployment packaging
configuration required to reproduce the reviewed implementation:

- `.vercelignore` — prevents QA data, generated skill trees, local databases,
  and workbooks from entering a Vercel deployment bundle.
- `backend/app/api/routes/ai.py` — AI request validation, rate limiting,
  RIASEC evaluation, and career-focus context.
- `backend/app/api/routes/learning.py` — career-goal limits and career-context
  skill-plan response.
- `backend/app/api/routes/profile.py` — profile updates and synthetic-data
  provenance behavior.
- `backend/app/api/routes/tasks.py` — task/tag loading and scheduling capacity
  validation.
- `backend/app/core/config.py` — environment-specific CORS defaults and
  allowlist behavior.
- `backend/app/core/database.py` — enables SQLite foreign-key enforcement.
- `backend/app/core/rate_limit.py` — shared in-process sliding-window and
  lockout limiter implementations used by AI routes.
- `backend/app/main.py` — permits PATCH in CORS preflight handling.
- `backend/app/models/user.py` — maps the persistent `is_synthetic` user
  column.
- `backend/app/schemas/user.py` — exposes synthetic provenance in the user
  schema.
- `backend/app/services/ai.py` — evidence-preserving CV normalization,
  roadmap career context, and structured RIASEC evaluation.
- `backend/app/services/career_matching.py` — current multi-year academic and
  grade-bounded recommendation behavior; preserve its validated rules.
- `backend/app/services/skill_planner.py` — ranked recommendation and selected
  career context for skill plans.
- `components/header.html` — adds the task-calendar navigation entry.
- `css/global.css` — styles the career-focus, certificate validation, profile,
  and RIASEC evaluation UI.
- `js/app.js` — certificate score validation and profile score normalization.
- `js/auth.js` — surfaces retry timing from rate-limited API responses.
- `js/certificates.js` — certificate score sanitizing, validation, and
  canonical formatting.
- `js/cv-builder-editor.js` — explicit AI normalization, local draft
  persistence, cooldown handling, and editing behavior.
- `js/dashboard.js` — current server-backed evaluation flow and certificate
  UI behavior.
- `js/riasec.js` — 60-question balanced assessment, draft-version handling,
  score calculation, and AI evaluation request.
- `pages/cv-builder-editor.html` — consent/behavior copy for CV AI and editor
  save guidance.
- `pages/dashboard.html` — accessible status output for evaluation.
- `pages/development.html` — current career-focus and server-generated
  roadmap/task presentation.
- `pages/profile.html` — accessible profile fields and certificate score
  validation UI.
- `pages/riasec.html` — current assessment instructions and AI evaluation
  presentation.

These changes depend on unchanged application files already present in HEAD,
including shared auth/data helpers, the registered API routers, existing
assessment and task models, and the corresponding unchanged page assets.

## Database migration

- `backend/alembic/versions/0011_add_user_synthetic_marker.py` — required
  runtime schema migration. It adds `users.is_synthetic BOOLEAN NOT NULL
  DEFAULT false`, which is mapped by `backend/app/models/user.py` and read by
  `backend/app/api/routes/profile.py`.
  - Revision: `0011_add_user_synthetic_marker`
  - `down_revision`: `0010_create_tasks`
  - Dependency: the existing, tracked migration
    `backend/alembic/versions/0010_create_tasks.py`.
  - `upgrade()` adds the column; `downgrade()` drops it.
  - The Alembic version chain discovers it from the versions directory; no
    separate migration metadata change is required.
  - Do not execute this migration as part of this scope review. Production
    migration state remains **UNVERIFIED**.

Without the column, requests using the mapped `User` model against a database
that has not been migrated can fail when profile code accesses
`user.is_synthetic`. Migration 0011 is required in the release source set;
whether it has already been applied in production must be checked separately
through an approved process.

## Tests required for release verification

These 10 tests directly cover changed runtime behavior and should accompany
the proposed code:

- `backend/tests/test_ai_cv.py` — CV normalization constraints and limiter
  concurrency/lockout behavior.
- `backend/tests/test_api_integration.py` — API integration, profile
  provenance, career-focus, rate-limit, and career-goal behavior.
- `backend/tests/test_career_matching.py` — recommendation calculations,
  multi-year aggregation, grade bounds, and workbook regression cases.
- `backend/tests/test_config.py` — environment-specific CORS configuration.
- `backend/tests/test_documents.py` — per-user document privacy and access.
- `backend/tests/test_goal_append.py` — career-goal limits and reactivation
  behavior.
- `backend/tests/test_task_planner.py` — task capacity, planning, and deferral
  behavior.
- `tests/frontend-smoke.mjs` — frontend behavior/layout smoke coverage.
- `backend/tests/test_database.py` — SQLite foreign-key enforcement.
- `backend/tests/test_riasec_evaluation.py` — RIASEC evaluation request,
  validation, and AI response structure.

The first eight paths are modified tracked files; the final two are untracked
and required test files. They rely on the existing backend test dependencies
and application modules from the checkout; they do not require production
access or a production migration.

## Documentation-only files

These two tracked files describe the included CORS behavior and should be
carried with the related implementation, although neither is needed to execute
the application:

- `README.md` — documents the development loopback origins.
- `backend/README.md` — documents development and production CORS behavior.

## QA-only artifacts

Keep these as QA evidence or validation tools, but do not put them in the
production deployment bundle:

- `validate_workbook.py` — offline workbook validator; it requires the
  separately held canonical SQLite snapshot identified by its SHA-256 in the
  report. That fixture is not part of Git, so exact canonical replay is not
  reproducible from a clean checkout alone.
- `students_anonymized_30.xlsx` — synthetic QA workbook; it is not an
  application runtime dependency.
- `.qa/PRE_DEPLOYMENT_AUDIT.md` — human-readable audit evidence.
- `.qa/PRE_DEPLOYMENT_AUDIT.json` — machine-readable audit evidence.

The `.vercelignore` policy excludes QA artifacts and `*.xlsx` from deployment.
The workbook validator does not justify altering or regenerating the workbook
as part of this release-scope task.

## Explicitly excluded files

Do not include these files or patterns in the proposed production release.
Do not delete them:

- `.agents/skills/vercel-react-best-practices/**` — generated/local skill
  content, not application code.
- `.claude/skills/vercel-react-best-practices/**` — duplicate generated/local
  skill content, not application code.
- `skills-lock.json` — local skill metadata, not an application dependency.
- `data/**` — local generated validation data, not runtime data.
- `tools/synthetic_students.py` — local synthetic-data generation utility,
  not required to run the application or its selected tests.
- `students_anonymized_30_FIXED.xlsx` and
  `students_anonymized_30_rebuilt.xlsx` — alternate generated workbook copies;
  neither is required for this release.
- `.qa/accounts_created_since_2026-09-29-1600.xlsx` — local audit export, not
  runtime material.
- `.qa/**` reports and files not listed under “QA-only artifacts” or
  “Uncertain files” — temporary, historical, or unrelated audit outputs,
  not release dependencies.
- `.env`, `.env.*`, `**/.env`, `**/.env.*`, `**/*.db`, `**/*.sqlite`, and
  `**/*.sqlite3` — local configuration/data; never package credentials or
  local database snapshots.
- `node_modules/**`, `.neon/**`, `.vercel/**`, and other local caches/config
  artifacts — not part of the reviewed release changes.

The root workspace also has untracked items outside this nested `FuturePath`
Git repository. They are outside this manifest's scope and have not been
included or modified.

## Uncertain files

These two QA reports are not runtime dependencies, but their suitability as
current parity evidence is unresolved:

- `.qa/WORKBOOK_PARITY_VALIDATION.md` — currently records historical
  `30/30` replay but also reports `8/30` current-engine/reference agreement
  and `parity_status: not_verified`.
- `.qa/WORKBOOK_PARITY_VALIDATION.json` — contains the same older
  `source_mismatch_count: 22` result and `parity_status: not_verified`.

This conflicts with the prior reconciliation summary's later successful
current-engine/workbook result. Before treating either report as current
evidence, reconcile or regenerate the reports with the correct canonical
fixture and validator version, then review the resulting diff. No such
regeneration is performed by this manifest.

## Modified tracked file classification

Every one of the 37 modified tracked paths is assigned exactly one category:

### A. REQUIRED FOR RELEASE

`.vercelignore`; `backend/app/api/routes/ai.py`;
`backend/app/api/routes/learning.py`; `backend/app/api/routes/profile.py`;
`backend/app/api/routes/tasks.py`; `backend/app/core/config.py`;
`backend/app/core/database.py`; `backend/app/core/rate_limit.py`;
`backend/app/main.py`; `backend/app/models/user.py`;
`backend/app/schemas/user.py`; `backend/app/services/ai.py`;
`backend/app/services/career_matching.py`;
`backend/app/services/skill_planner.py`; `components/header.html`;
`css/global.css`; `js/app.js`; `js/auth.js`; `js/certificates.js`;
`js/cv-builder-editor.js`; `js/dashboard.js`; `js/riasec.js`;
`pages/cv-builder-editor.html`; `pages/dashboard.html`;
`pages/development.html`; `pages/profile.html`; `pages/riasec.html`.

### B. REQUIRED ONLY FOR TEST/QA

`backend/tests/test_ai_cv.py`; `backend/tests/test_api_integration.py`;
`backend/tests/test_career_matching.py`; `backend/tests/test_config.py`;
`backend/tests/test_documents.py`; `backend/tests/test_goal_append.py`;
`backend/tests/test_task_planner.py`; `tests/frontend-smoke.mjs`.

### C. DOCUMENTATION ONLY

`README.md`; `backend/README.md`.

### D. PRE-EXISTING / UNRELATED

None identified among the 37 modified tracked paths.

### E. UNCERTAIN — requires manual review

None of the 37 modified tracked paths. The two uncertain workbook parity
reports above are untracked QA artifacts, not part of this tracked-file
classification.

## Dependency summary

- Profile provenance: migration 0011 → `User.is_synthetic` ORM mapping and
  user schema → profile API route.
- AI/CV/RIASEC behavior: AI API route → rate-limit helpers and `AIService` →
  frontend auth/API helpers and the CV/RIASEC pages.
- Learning/career focus: learning and AI routes → `skill_planner.py`,
  assessment/goal/task models, and existing persistence dependencies →
  development page.
- Task behavior: task API route → existing task/tag models and planner →
  development page and task/calendar navigation.
- Recommendations: existing assessment route → `career_matching.py` →
  dashboard and workbook regression tests; preserve the current validated
  multi-year behavior.
- Certificate behavior: `certificates.js` → profile and shared application
  code, with validation styles in `global.css`.
- Frontend pages use existing shared header, CSS, auth, and data assets from
  HEAD; those unchanged dependencies remain part of any clean checkout.

## Proposed counts and reproducibility

- Application runtime/config changes: **27 tracked files**.
- Required database migration: **1 untracked file**.
- Required verification tests: **10 files** (8 tracked changes, 2 untracked).
- Related documentation-only changes: **2 tracked files**.
- QA evidence/tooling listed above: **4 files**.
- Uncertain QA reports: **2 files**.
- Other currently untracked paths excluded from this proposal: **209 paths**
  based on the observed 218 untracked paths before creating this manifest.
- No files are staged or committed by this proposal.

A clean checkout at HEAD plus the proposed runtime, migration, tests, and
documentation files can reproduce the application and repository test scope
in principle, subject to installing the declared dependencies. It cannot
reproduce the canonical workbook parity run from Git alone because the pinned
SQLite source fixture is external to the repository. Production configuration
and migration state remain separate unverified blockers.

## Remaining release blockers

### P0

- Production Vercel values for `ENVIRONMENT`, `COOKIE_SECURE`, and
  `CORS_ORIGINS` are missing or unverified in the audit evidence.
- Production Alembic revision is **UNVERIFIED**; do not infer whether 0011 is
  applied.
- The validated implementation is not yet represented by a reviewed release
  commit; current `HEAD` alone does not reproduce the worktree.

### P1

- AI rate limiting is process-local and is not a global limit across serverless
  instances.
- SDK timeout/retry defaults have not been verified against function runtime
  limits.
- Production build and provider behavior have not been verified.

No deployment, production access, production migration, push, stage, or commit
is authorized by this manifest.
