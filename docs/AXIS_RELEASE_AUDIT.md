# AXIS release audit: current implementation

Updated: 2026-10-06

## Evidence baseline

| Check | Result | Evidence / limitation |
|---|---|---|
| Frontend smoke | PASS, 24 tests before implementation | `npm run test:frontend` on the current checkout |
| Backend suite | PASS, 77 tests before implementation | `python -m pytest tests -q`; two upstream deprecation warnings |
| TypeScript build | PASS before implementation | `npm run build` |
| Lighthouse mobile baseline | RECORDED locally | Lighthouse 13.5.0, same headless mobile configuration over local HTTP; lab results are not field p75 |
| Production schema/provider | NOT VERIFIED | Existing QA evidence says the deployed DB identity and migration state are unconfirmed |

## Implementation verification (2026-10-06)

| Check | Result | Evidence / limitation |
|---|---|---|
| Frontend smoke | PASS, 27/27 | `npm run test:frontend` |
| Backend suite | PASS, 91 passed | `python -m pytest tests -q`; two upstream Starlette/AnyIO deprecation warnings |
| TypeScript build | PASS | `npm run build` |
| Production read-only smoke | PASS, HTTP 200 | GET `/health` and `/health/ready` on the current Vercel deployment; this checks the deployed version, not the uncommitted working tree |
| Diff whitespace check | PASS | `git diff --check`; Git reports expected LF-to-CRLF conversion notices for three HTML files |

Changes in this implementation include server-owned benchmark scoring, input bounds, stable ranking and score explanations; RIASEC result restoration; bounded process-local login lockout; reduced sensitive exception logging; prioritized WebP LCP images and deferred scripts on measured pages. Production files, database, accounts and migrations were not changed.

### Follow-up verification (2026-10-06)

| Check | Result | Evidence / limitation |
|---|---|---|
| Frontend smoke | PASS, 27/27 | `npm run test:frontend` on the current working tree |
| Python backend suite | PASS, 94 passed | `python -m pytest -q`; one upstream Starlette/AnyIO deprecation warning |
| TypeScript build | PASS | `npm run build` |
| RIASEC browser flow | PASS | Local Chrome/Playwright completed all 60 answers, submitted, verified result persistence and restoration after reload; guest profile only, no authenticated server sync |
| Node auth static check | PASS | `npm run check` |
| Node auth security integration | PASS | Isolated local MongoDB and port 3301, `NODE_ENV=production`: registration, login cookie flags, refresh rotation/reuse detection, and rate limiting (429); temporary database was dropped after test |
| Working diff check | PASS | `git diff --check`; Git emitted line-ending notices only |

The Vercel configuration now derives production/preview environment and secure-cookie defaults from Vercel runtime variables, and rejects weak production secrets; config tests are included in the 94-test backend run. These changes have not been deployed or verified against provider settings. A first auth-test invocation without a running local service failed to connect; the successful integration run used an isolated temporary service and database.

## Severity, dependency and release priority

1. **P0 – Core AXIS truth:** source and validate the 24 career records; reconcile the two matching paths; obtain recorded approval for expected golden outputs. These depend on domain evidence and are not resolved by code-only tests.
2. **P1 – Privacy and production boundary:** verify ownership/authorization, private file access, upload, session, shared rate limiting, production topology, migration and restore/rollback. Read-only health checks do not verify these.
3. **P2 – Critical UX:** exercise real browser refresh/deep-link/session flows and the complete profile → assessment → match → roadmap path against a persisted environment.
4. **P3 – Performance follow-up:** profile/dashboard/career detail remain over the reference LCP; optimize measured CSS/font render blockers only after confirming their impact, then remeasure on the same setup.

There are no unresolved Critical findings identified by these local checks. High findings above remain open and need impact, named owner, and dated handling records before release; no such approval/owner record was available in the repository during this implementation.

## Findings and priority

| Severity | Finding | Dependency / next action |
|---|---|---|
| High | `/api/v1/axis/evaluate` accepted benchmark definitions from the browser and used them for scoring and persisted results. | Fixed in this change: scores are validated; the route reads the server catalog, returns stable ranks and criterion contribution explanations. Re-run route and dashboard regressions. |
| High | The 24 seeded benchmarks have empty AHP matrices. The calculation engine therefore uses ROC fallback for these rows; the deployed seeded catalog does not exercise AHP weights. Targets are generated from rank positions, not a referenced career standard. | Requires domain evidence and an accepted career dataset before freezing expected rankings. Do not describe seeded output as validated AHP-SAW-ROC. |
| High | Assessment history (`/assessments/run`) uses `career_matching.calculate_matches`, while the AXIS dashboard uses `calculation_engine.calculate_hybrid`. These are distinct scoring paths and can produce different percentages/rankings. | Map their product roles and select/approve a source of truth before consolidating. A behavior change here requires reviewed golden outputs. |
| High | Skills, roadmap, RIASEC rationale, salary and matching criteria have no field-level sources or approval records. | Official Vietnam taxonomy sources now replace broad international university links on the detail page; those sources support the official lists, not every AXIS claim. Complete field-level evidence and approval before freezing the dataset. |
| Medium | Completed RIASEC result did not restore its result view on refresh, although it was stored in user-scoped local storage/profile data. | Fixed in this change: validated saved results render on load, auth change, and profile hydration. Verify browser refresh and account-switch flows. |
| Medium | Seven large hero PNGs total about 9.64 MB. Homepage/profile/dashboard LCP traces identified `hero-2.png` as a large delivery cost; career detail rewrote its eager LCP image to an external Unsplash URL in inline JavaScript, making the request undiscoverable in the document. | The measured `hero-2` asset is now WebP and prioritized. Career detail now uses a local WebP illustration, declares dimensions/priority, and waits for deferred auth before its API reads. |
| Medium | AI limits were process-local and login had no route-level limiter. | A bounded per-process hashed-email failure limiter now blocks after five failed logins. Both it and AI limiting still need a shared-store design if production runs multiple instances. |

## Career catalog audit

The catalog has codes N01–N24. Each backend `Industry` record provides a display name, two related school subjects, two RIASEC letters, and an ordering of S1–S5. The page has static descriptions, skills and suggested activities. Its old international institution links have been replaced with Vietnamese official taxonomy links and a scope caveat. These legal sources do not validate the local institution/program mapping, skills, roadmap, RIASEC rationale, salary or matching weights; those need separate field-level provenance.

| Catalog coverage | Current status |
|---|---|
| Names (N01–N24) | Present in backend catalog; compare with frontend detail labels for parity |
| Related study fields / subjects | Two school subjects per group; higher-education program mapping not represented in the backend record |
| Skills and learning activities | Present as static detail-page content; no field-level source citation found |
| RIASEC association | Two letters per group; rationale and validation source not recorded |
| Matching criteria | S1–S5 order exists; seeded min/max are generic 0–10 and targets are rank-derived |
| Roadmap | Suggested static activities exist; no traceable relationship to measured gaps is established for every career |
| Sources and freshness | One broad study-area reference link is present per career detail; no source date or field-level provenance |
| Confirmed gaps | All 24 domains need source/provenance review, especially local degree/program mapping and salary evidence; a broad reference link does not validate every displayed field |

## Calculation and reproducibility notes

- `calculation_engine.py` normalizes each criterion, normalizes AHP/ROC weights, blends the selected AHP or ROC vector with ROC, computes weighted SAW match, and calculates weighted RMS gap risk.
- The active seeded catalog has no AHP matrices, so it currently follows the ROC fallback path. The generic targets drive gap-risk but, with min=0/max=10, do not drive the match percentage.
- `/axis/evaluate` now uses the server-owned catalog instead of trusting client benchmark requirements. Each result includes per-criterion normalized input, weight, target, and score contribution; contributions sum to the unrounded SAW percentage within rounding tolerance.
- `career_matching.py` also contains a separate legacy/domain-specific scoring algorithm. Matching golden cases are not approved until the product owner records expected outputs in the evidence matrix or test documentation.
- Certificate expiry in `career_matching.py` depends on the evaluation date. A reproducibility fixture must pin an evaluation date or include it in its recorded input context.

## Lighthouse lab comparison

One local headless mobile run per page, with Lighthouse 13.5.0 and the same local HTTP server/configuration before and after the measured image/script changes. Scores are lab runs and may vary between runs. No field p75 or INP value was collected.

| Page | Perf score before → after | LCP before → after | TBT before → after | CLS before → after |
|---|---:|---:|---:|---:|
| Home | 0.62 → 0.93 | 11.3 s → 2.6 s | 220 ms → 150 ms | 0 → 0 |
| Profile | 0.43 → 0.72 | 11.0 s → 4.8 s | 1,040 ms → 70 ms | 0.015 → 0.017 |
| Dashboard | 0.56 → 0.70 | 9.6 s → 5.3 s | 670 ms → 90 ms | 0.017 → 0.018 |
| Career detail | 0.44 → 0.65 | 13.5 s → 5.5 s | 1,090 ms → 90 ms | 0.003 → 0 |

On the home run, Lighthouse estimated 1,349 KiB savings for the 1.40 MB `hero-2.png`, whose source was 1254×1254 and displayed at roughly 315×315. After replacement with the 44 KB 800×800 WebP and deferring critical-page scripts, the home LCP fell to 2.6 s. The career-detail image was initially a JavaScript-assigned remote URL and not discoverable in the document; it now uses a prioritized local WebP, and the final run improved LCP from 13.5 s to 5.5 s. Profile/dashboard and career detail still show render-blocking Google Fonts/shared CSS and LCP above the 2.5 s reference; those remain measured follow-up bottlenecks.

## Release boundary

No production database, account, provider configuration, or deployment was changed. Production DB identity, migration execution, backup/restore, and Vercel/Render topology remain external verification items. The release should remain blocked until High findings have documented decisions and all Critical issues are cleared.
