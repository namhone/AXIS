# AXIS career dataset audit

**Catalog:** [`data/career-catalog.v1.json`](../data/career-catalog.v1.json)  
**Audit date:** 2026-10-06  
**Status:** Draft for domain review; do not freeze or use as an approved matching golden dataset.

## Scope and source interpretation

N01–N24 are treated as AXIS product groupings using the names supplied by the project owner. The official classification documents are source references for the national lists of programs and occupations; this audit does not claim that the 24 AXIS labels are the verbatim statutory group names or codes.

The Government legal-document portal records Circular 74/2026/TT-BGDĐT for higher education program taxonomy, effective 12 October 2026. Circular 77/2026/TT-BGDĐT covers vocational education and is effective 1 December 2026. Both have been promulgated but are not yet effective on the audit date. The Government article describes the new AI, industrial robot, railway infrastructure, and renewable-energy occupations and confirms the latter effective date.

## 24 group coverage

All 24 AXIS records now have canonical display labels. The current mapping data already contains two related high-school subjects, two RIASEC letters, and a five-criterion priority order per group. The current weight vector is derived from that existing priority order with the ROC weights. These fields are retained as the live heuristic; the official lists do not establish their correctness for career guidance.

| Field | Current coverage | Evidence / limitation |
|---|---|---|
| AXIS group name | 24/24 | Supplied list; consistent labels in backend matching, dashboard fallback, career listing and detail page |
| Official degree-program codes and names | Not mapped | Full annex and institution-level program availability must be mapped before claiming a program is offered in a particular place |
| Vocational programs / occupations | 12 new entries recorded | Source names copied from the Government article; proposed mappings to AXIS groups are hypotheses, not official crosswalks |
| High-school subjects | 24/24 have two | Existing AXIS heuristic, not official admission requirements |
| Skills and roadmaps | Static content exists | AXIS-authored page content; no field-level source or reviewer record |
| RIASEC | 24/24 have two letters | Legacy assessment route uses each group's RIASEC tuple. Dashboard Hybrid receives a single S4 score and does not receive/read the group's RIASEC tuple; S4 can still affect match indirectly through its weight. The two routes therefore do not mean the same thing. |
| Matching criteria | S1–S5 order exists for all 24 | Existing order and ROC weights retained; no approved career-specific evidence or golden outputs |
| Salary | Removed from career detail | Existing figures lacked Vietnamese source, survey date, location and experience bands |
| Provenance / review date | Added for official lists only | Skills, roadmap, RIASEC, criteria and future program mappings still need field-level provenance and review |

## New vocational entries

The 12 occupations from the supplied Government source are recorded in `newVocationalPrograms`. Candidate mappings are:

- AI, applied AI, AI robotics → N01 and/or N21; industrial robotics → N06 (with N01 as a secondary candidate).
- Railway signaling, AFC, railway electrical systems and traction dispatch → N06 and N20.
- Renewable-energy installation and wind/solar plant operation → N06 and N13.

These links are marked `proposed_only_unverified`. They should not affect ranking or be described as an official crosswalk until the full legal annex and local institution offerings are checked.

## Matching boundary

Only display labels and the career-detail source presentation changed in this audit. The matching formula, criteria, weight values, normalization, thresholds and ranking behavior were not changed. The current dashboard API uses the Hybrid AHP-SAW-ROC engine; the assessment-history route also has a separate legacy `career_matching.calculate_matches` implementation. This audit does not merge those paths.

The attached design text describes fixed Min–Max scaling and a minimum-threshold elimination step. The running implementation must be treated as the requested source of truth for now; those design-text details are not introduced as code changes. Record and resolve this discrepancy during model validation before creating approved golden cases.

One additional business gap is verified in code: `/assessments/run` calculates an industry-specific RIASEC component from the two stored letters, while `/axis/evaluate` sends only S1–S5 into `calculate_hybrid`; its benchmark input contains no industry RIASEC letters. The dashboard's S4 score can influence the weighted total, but it is not compared against the selected group's RIASEC profile. I left this behavior unchanged per instruction to preserve the current live formula; it needs a product decision and reviewed golden cases.

## Release work still required

1. Map every AXIS bucket to exact program codes/names in the new higher-education annex and mark multiple/uncertain mappings explicitly.
2. Verify which Vietnamese institutions currently offer each mapped program, with official source URL and checked date.
3. Attach dated, field-level sources to skills, learning activities, salary information (if restored), RIASEC rationale, and career criterion priorities.
4. Have expected matching outputs reviewed and record the reviewer/date in the evidence matrix before treating golden cases as regression truth.
5. Version the reviewed dataset separately from this draft and rerun the existing formula's golden/edge cases on every later data or model change.

## Primary sources

- [Circular 74/2026/TT-BGDĐT, official Government legal-document portal](https://vanban.chinhphu.vn/?classid=1&docid=219455&orggroupid=4&pageid=27160) — issued 28 August 2026; effective 12 October 2026.
- [Circular 77/2026/TT-BGDĐT, official Government legal-document portal](https://vanban.chinhphu.vn/?classid=1&docid=219658&orggroupid=4&pageid=27160) — issued 25 September 2026; effective 1 December 2026.
- [Government article summarizing new vocational programs and occupations](https://baochinhphu.vn/danh-muc-nganh-nghe-dao-tao-trong-giao-duc-nghe-nghiep-102260928083810846.htm) — technology, railway infrastructure and energy entries; article dated 28 September 2026.
