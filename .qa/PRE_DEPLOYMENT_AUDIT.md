# FuturePath Pre-Deployment Audit

**Audit date:** 2026-09-29
**Scope:** Read-only production-readiness review. No deployment, production migration, production database query, or application/workbook edit was performed.

## 1. Executive summary

**Verdict: NOT READY FOR DEPLOY**

There are two deployment-blocking areas:

1. The linked Vercel project's production environment has `DATABASE_URL`, `GROQ_API_KEY`, and `JWT_SECRET_KEY`, but not `ENVIRONMENT`, `COOKIE_SECURE`, or `CORS_ORIGINS`. The application defaults to development settings when `ENVIRONMENT` is absent; this leaves `COOKIE_SECURE=false` and enables development CORS origins. The secret values were not read or printed.
2. Production's Alembic revision is unverified. The local database is at `0010_create_tasks`; repository migration head is `0011_add_user_synthetic_marker`. The current worktree also has migration 0011 untracked, and the Vercel configuration has no migration hook. The profile API accesses `User.is_synthetic`, which requires the 0011 schema.

The recommendation specification and workbook parity checks pass against the approved current model: 30/30 profiles and 90/90 Top-1/Top-2/Top-3 slots. The 22 saved-assessment differences are expected: all 22 are caused by multi-year subject averaging; none are due to GPA changes. They are not deployment blockers.

No application code or workbook was changed during this audit. Only the two requested audit reports are newly created by this audit.

## 2. Git/worktree

| Item | Result |
|---|---|
| Branch | `main` |
| HEAD | `bb9a8a9e9c3e825e57650475bf4682bc51df7179` |
| Staged paths before writing audit reports | 0 |
| Modified tracked paths before writing audit reports | 37 |
| Untracked paths before writing audit reports | 179 |
| Changes created by this audit | `.qa/PRE_DEPLOYMENT_AUDIT.md`, `.qa/PRE_DEPLOYMENT_AUDIT.json` |

The 37 pre-existing modified tracked paths are:

`.vercelignore`, `README.md`, `backend/README.md`, `backend/app/api/routes/ai.py`, `backend/app/api/routes/learning.py`, `backend/app/api/routes/profile.py`, `backend/app/api/routes/tasks.py`, `backend/app/core/config.py`, `backend/app/core/database.py`, `backend/app/core/rate_limit.py`, `backend/app/main.py`, `backend/app/models/user.py`, `backend/app/schemas/user.py`, `backend/app/services/ai.py`, `backend/app/services/career_matching.py`, `backend/app/services/skill_planner.py`, `backend/tests/test_ai_cv.py`, `backend/tests/test_api_integration.py`, `backend/tests/test_career_matching.py`, `backend/tests/test_config.py`, `backend/tests/test_documents.py`, `backend/tests/test_goal_append.py`, `backend/tests/test_task_planner.py`, `components/header.html`, `css/global.css`, `js/app.js`, `js/auth.js`, `js/certificates.js`, `js/cv-builder-editor.js`, `js/dashboard.js`, `js/riasec.js`, `pages/cv-builder-editor.html`, `pages/dashboard.html`, `pages/development.html`, `pages/profile.html`, `pages/riasec.html`, `tests/frontend-smoke.mjs`.

The 179 pre-existing untracked paths comprise 75 files under `.agents/skills/vercel-react-best-practices/`, 75 duplicate files under `.claude/skills/vercel-react-best-practices/`, and these 29 other paths:

- `.qa/AXIS_PRODUCTION_EXCEL_AUDIT.md`, `.qa/COVERAGE.md`, `.qa/FINAL_VERIFICATION_REPORT.md`, `.qa/FINAL_VERIFICATION_RESULTS.json`, `.qa/FINDINGS.md`, `.qa/FULL_SYSTEM_AUDIT.md`, `.qa/FULL_SYSTEM_MAP.md`, `.qa/FULL_SYSTEM_RESULTS.json`, `.qa/FUNCTIONALITY_MATRIX.md`, `.qa/LAST_RUN.md`, `.qa/REGRESSION_COVERAGE.md`, `.qa/SYSTEM_MAP.md`, `.qa/WORKBOOK_PARITY_VALIDATION.json`, `.qa/WORKBOOK_PARITY_VALIDATION.md`, `.qa/accounts_created_since_2026-09-29-1600.xlsx`, `.qa/axis_audit_results.json`, `.qa/test_mobile_cv_layout.py`
- `backend/alembic/versions/0011_add_user_synthetic_marker.py`
- `backend/tests/test_database.py`, `backend/tests/test_riasec_evaluation.py`
- `data/validation_calculations.csv`, `data/validation_report.md`, `data/validation_students.csv`
- `skills-lock.json`, `students_anonymized_30.xlsx`, `students_anonymized_30_FIXED.xlsx`, `students_anonymized_30_rebuilt.xlsx`, `tools/synthetic_students.py`, `validate_workbook.py`

**Deployment implication:** tests were run against this dirty worktree. A deployment from HEAD will not include these modified or untracked changes. Do not reset or revert them; first identify and commit/release only the intended, reviewed changes. The migration's untracked status is especially important.

**Secrets/suspicious files:** local `.env.local` and `backend/.env` are ignored and were not found among tracked files. The security review found no obvious committed-secret patterns in tracked text. Secret values were not printed. The untracked migration, multiple workbook copies, and extensive skill trees should be reviewed before staging. `.vercelignore` excludes environment files, databases, QA/development content, and XLSX files from Vercel packaging.

## 3. Backend

### Request and data flow

The FastAPI app exposes authenticated profile and recommendation paths; profile serialization accesses the `User.is_synthetic` ORM field. API failures use generic client-facing server errors rather than returning stack traces. Avatar upload validation checks MIME/signature and enforces a 5 MB limit. The reviewed routes did not reveal an obvious missing authentication check, SQL injection, or unsafe dynamic execution.

### Production configuration

The linked Vercel production environment was queried for **variable names only**:

| Variable | Name present? | Audit result |
|---|---:|---|
| `DATABASE_URL` | Yes | Value and connectivity not inspected |
| `GROQ_API_KEY` | Yes | Value/validity not inspected |
| `JWT_SECRET_KEY` | Yes | Value/length not inspected |
| `ENVIRONMENT` | No | Application defaults to `development` |
| `COOKIE_SECURE` | No | Default is `false`; production should require `true` |
| `CORS_ORIGINS` | No | Development-mode fallback includes localhost origins |

The production validator in application settings enforces a 32-character JWT secret and secure cookies only when `ENVIRONMENT=production` (or `prod`). As observed, Vercel's variable names do not activate that validation. Set and verify the production values in the Vercel project before release; do not place secret values in this report.

`render.yaml` declares production environment settings, but the actual Render dashboard values were not accessible/verified in this audit. This does not establish that Vercel and Render production environments are identical.

### API/operational behavior

- API base selection is same-origin `/api/v1` for non-local hosts; localhost URLs are local-development fallback paths.
- CORS rejects wildcard origins in configuration. However, absent `ENVIRONMENT` causes the development origin list to be selected.
- The AI request limiter is process-local. It cannot enforce one global limit across serverless instances or multiple workers.
- The readiness route executes `SELECT 1`; it does not verify Alembic head or required columns.
- The OpenAI-compatible SDK is initialized without application timeout/retry overrides; the SDK defaults are 600 seconds and two retries. Compatibility with the Vercel function duration was not verified.
- No production runtime/browser session was exercised.

## 4. Database/migrations

| Check | Result |
|---|---|
| Repository Alembic head | `0011_add_user_synthetic_marker` |
| Local `backend/dev.db` revision | `0010_create_tasks` |
| Local DB contains 0011 column | No; local revision precedes migration |
| Production DB revision | **Not verified**; no production connection/query/migration was run |
| Migration 0011 | Untracked; adds `users.is_synthetic BOOLEAN NOT NULL DEFAULT false`; downgrade drops the column |
| Vercel migration hook | None |
| Render migration hook | `preDeployCommand: alembic -c alembic.ini upgrade head` |

The local Alembic check reports the target database is not up to date. This is an expected local schema/revision mismatch and was not fixed by running a migration. The production schema must be checked and migrated through an approved pipeline before code requiring `is_synthetic` is served. Render's hook only helps if that service and a commit containing migration 0011 are actually used; it does not establish the Vercel database state.

The root README migration-head note is stale (`0009` vs the current repository head `0011`).

## 5. Recommendation engine regression

The approved specification remains unchanged:

- Average every valid populated year for each subject and for matching GPA; missing values do not enter the denominator.
- Include valid `gpa9`.
- Do not infer numeric grade from `className`.
- Preserve S1 weights `0.35 / 0.35 / 0.30`; preserve S2–S5 and ranking logic.

Results:

| Comparison | Result |
|---|---:|
| Current engine vs canonical `Profile.data`, Top 1 | 30/30 |
| Current engine vs canonical `Profile.data`, Top 2 | 30/30 |
| Current engine vs canonical `Profile.data`, Top 3 | 30/30 |
| Engine-to-workbook recommendation score comparisons | 90/90 |
| Current engine exact Top 3 vs saved historical assessments | 8/30 |
| Historical Top 3 differences | 22/30 |

The 22 differences have one reported cause: `multi_year_subject_aggregation` (22 profiles). The synthetic replay reports zero profiles with GPA changes. Nine profiles have changed career names; the other 13 have score-only differences. This is consistent with the approved multi-year rule and is not a regression. The latest validator exits 1 with `completed_with_source_differences`, not a runtime error, because it also compares against saved historical assessments. Its current-engine-to-workbook comparison is 30/30 for each rank.

## 6. Workbook

The workbook was opened successfully and not modified during this audit.

| Sheet | Dimensions | Filter | Freeze panes | Merged ranges | Formulas / cached results | Formula errors |
|---|---|---|---|---:|---:|---:|
| `Tổng hợp` | A1:I31 | A1:I31 | A2 | 0 | 30 / 30 | 0 |
| `Môn học` | A1:Z31 | A1:Z31 | E2 | 0 | 52 / 52 | 0 |
| `Hồ sơ` | A1:L31 | A1:L31 | A2 | 0 | 0 / 0 | 0 |

There are 30 profile rows, 90 recommendation slots, three sheets, no formula errors, and cached values for all 82 formulas. Column order, filters, freeze panes, merged ranges, styled row heights and widths were inspected. No workbook regeneration or update was performed in this audit.

### Input divergence and limits

The approved workbook synchronization record documents the earlier **553 academic-field changes/touches** as 417 existing Grade 10–11 subject cells updated, 84 Grade 12 values not representable in the existing layout, and 52 GPA formulas written/updated. These figures are not 553 current mismatches: the record says all 600 existing Grade 10–11 subject cells now match canonical inputs, while 84 Grade 12 values remain outside the workbook. Ten of the GPA formula updates added previously missing Grade 11 formulas.

The workbook intentionally retained its existing layout and has no Grade 12 subject/GPA columns. It also lacks numeric RIASEC and some skills/activity inputs. It is therefore not a standalone source from which to reconstruct every recommendation. The current canonical engine-to-workbook result is verified, but a complete same-input reconstruction from workbook contents is not.

## 7. Frontend

- Frontend smoke tests: 24 passed.
- TypeScript `npm run build`: passed.
- API URL selection uses same-origin paths in non-local deployments; localhost values are development fallbacks.
- Protected route, profile/recommendation loading and error/empty handling were reviewed statically.
- Vercel headers include CSP, `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy`.
- No live production browser session or production console/network inspection was performed.
- The Vercel production builder was not run: non-interactive `vercel build --prod` required confirmation to pull production environment variables. The build was stopped rather than pulling/storing production values locally. This is a verification gap, not a production build failure.

## 8. Security

A focused security review of the backend routes, authentication/configuration, API entrypoint and frontend auth/rendering found no other obvious high-risk code vulnerability or committed-secret pattern in the reviewed paths. This is not a full penetration test.

**Confirmed configuration blocker:** Vercel production is missing `ENVIRONMENT` and `COOKIE_SECURE`; settings then use development defaults, including `cookie_secure=false`. This risks sending an authentication cookie over an unencrypted HTTP request and prevents production secret/cookie validation from running. It must be corrected before deployment. No secret values were disclosed.

Other reviewed controls include parameterized ORM/database access, protected profile routes, generic server errors, explicit-origin CORS validation, and upload type/size validation.

## 9. Dependencies/build

| Check | Result |
|---|---|
| Root `npm ls --depth=0` | Passed |
| `node-backend` `npm ls --depth=0` | Passed |
| Root and node-backend manifest/lock consistency | Passed |
| Python `pip check` | Passed |
| TypeScript build | Passed |
| Full production Vercel build | Not run; see Frontend |
| Dependency vulnerability database scan | Not run |

Backend tests emitted two Starlette/AnyIO deprecation warnings; no test failure was attributed to them. The `node-backend` security integration command failed to connect to `127.0.0.1:3001` because the local auth service was not running. This is an environment/service-unavailable result, not evidence of an application regression; the auth integration remains unverified by that test.

## 10. Deployment configuration

- `vercel.json` serves the repository root (`outputDirectory: "."`) and rewrites `/api/v1/*` and health routes to `api/index`; it defines security response headers and no migration hook.
- `render.yaml` installs Python dependencies, runs Alembic `upgrade head` as pre-deploy, starts Uvicorn, and defines a separate Node auth service. Dashboard values for database, CORS, AI key, MongoDB, auth secrets and frontend origin were not verified.
- `healthCheckPath: /health` is a static health response; `/health/ready` tests only database connectivity (`SELECT 1`), not schema revision.
- Production database migration status remains unverified. No production database was contacted.
- No deployment or production migration was performed.

## 11. Test results

| Area | Result | Classification |
|---|---|---|
| Full backend suite | 77 passed | Pass |
| Focused recommendation suite | 31 passed | Pass |
| Frontend smoke suite | 24 passed | Pass |
| TypeScript build | Passed | Pass |
| Canonical 30-profile recommendation replay | 30/30 Top 1, 30/30 Top 2, 30/30 Top 3 | Pass |
| Engine-to-workbook scores | 90/90 | Pass |
| Historical saved-assessment comparison | 8/30 exact; 22 differ due multi-year subject aggregation | Expected specification change |
| Workbook structure/formula audit | 3 sheets; 82 cached formulas; zero formula errors | Pass |
| Workbook validator process | Exit 1, `completed_with_source_differences`; no runtime error | Expected historical-reference difference; engine/workbook ranks are 30/30 |
| `alembic check` on local DB | Target not up to date; local current 0010, head 0011 | Local environment/schema status, not a production query |
| `node-backend` security integration | Connection refused at local port 3001 | Environment/service unavailable |
| `npm ls` (both packages), lock consistency, `pip check` | Passed | Pass |
| `git diff --check` | Passed | Manual whitespace check of the two new untracked reports also passed |
| Dedicated synthetic-generator unit test | No dedicated test was found | Gap; canonical dataset replay was run |
| Vercel production build | Not run to avoid pulling production secrets locally | Verification gap |

## 12. Blockers and findings

### P0 — Must fix before deploy

1. **Vercel production security settings are missing.** Set `ENVIRONMENT=production`, `COOKIE_SECURE=true`, and explicit production `CORS_ORIGINS`. Confirm the JWT secret meets the application's 32-character minimum without exposing it. Re-run a production-config validation.
2. **Required database revision is not verified and migration 0011 is untracked.** Confirm production is at the intended schema revision and apply 0011 through an approved migration process before serving code that uses `User.is_synthetic`. Include the migration in the reviewed release commit. No migration was run in this audit.
3. **No deployable artifact corresponds to the audited worktree yet.** The audited recommendation/config/migration changes are among 37 modified and 179 untracked paths, while HEAD remains `bb9a8a9e9c3e825e57650475bf4682bc51df7179`. Build and test the exact reviewed release commit before deployment; do not deploy HEAD expecting these worktree changes to be included.

### P1 — Should fix or explicitly accept before deploy

1. **AI rate limiting is process-local.** Across serverless instances/workers, the configured 5 requests per 60 seconds is not a global cap. Use shared enforcement or document/accept the residual cost-abuse risk.
2. **AI timeout compatibility is unverified.** SDK defaults are 600 seconds and two retries; compare the effective request duration with the production Vercel function limit and set explicit timeouts/retry behavior if necessary.
3. **Production validation gaps remain.** Run the Vercel build in a controlled CI environment that can use production settings without logging/seeding secret values. Verify live provider environment names/validity and migration state through approved access.

### P2 — Post-deploy or non-blocking

1. `/health/ready` verifies only a database round-trip and does not check Alembic/schema readiness.
2. Root README's stated migration head (`0009`) is stale.
3. No dedicated unit test for `tools/synthetic_students.py` was found; the canonical 30-profile replay passed.

### INFO

- The historical 22/30 recommendation difference is expected under the approved multi-year subject averaging behavior.
- Workbook Grade 12 and application-only RIASEC/skills/activity inputs cannot be fully represented in its existing layout.
- Two deprecation warnings and the unavailable local auth integration test are recorded above; neither is evidence of a newly introduced regression.

## 13. Final verdict

**NOT READY FOR DEPLOY**

Before deployment, at minimum:

1. Configure and validate Vercel production settings (`ENVIRONMENT`, secure cookies, explicit CORS, and secret validity).
2. Confirm production DB revision; include migration 0011 in the release and apply it only through the approved production migration process.
3. Selectively review and commit the intended worktree changes, then rerun tests against that exact release commit.
4. Complete a controlled production build and post-deploy smoke-test plan.

No deployment, production migration, production database change, workbook change, or recommendation-code change was made in this audit.
