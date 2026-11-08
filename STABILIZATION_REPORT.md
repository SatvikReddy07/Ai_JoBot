# Phase 4 reliability update — 8 November 2026

## Source of truth and handover comparison

The GitHub feature branch was read through the connected GitHub app before coding: `feature/phase4-assisted-applications` at `23b50af32936f8b857251e57f092d6b4ae9cb3d3`, source tree `60ba323e423b797ea08d9931ed11759e99d856ef`. The execution copy had different local commit IDs because prior publication used GitHub's commit API, but its source tree matched exactly. Its working tree was clean. GitHub `main` was still the older `3d8b0a3`.

| Handover item | Verified implementation |
| --- | --- |
| Phase 1–3 completed historically | Existing discovery, profile, local document generation, Studio, versions and approvals were retained and regression-tested |
| Phase 4 partially described | Router, models, Control Center, eligibility evidence, application approval, duplicate prevention, manual confirmation, outreach and reminders already implemented |
| Mac migration reportedly underway | Executable Mac launchers, authenticated shutdown, readiness checks and user-scoped launchd setup already present |
| Historical test counts 19 / 37 / 78 | Baseline was 93 tests; this update finishes with 125 passing tests |
| Historical 235 vacancies | Confirmed only in the uploaded source snapshot's database; the user's Mac data cannot be inferred from GitHub because data files are excluded |
| Submission support | Manual final submission and user-entered confirmation; optional allowlisted field preparation, not universal ATS automation |
| Migrations | Existing `initialize_schema()` backs up an existing database before adding missing tables. No Alembic/versioned column-migration framework is present. This update needs no table or column changes. |

## Changes implemented

### Matching and eligibility

A shared `matching_context.py` supplies candidate facts and current settings to discovery, fallback assessment and Phase 4 eligibility. Relevant technical skills, industry evidence and academic categories now depend on the profile rather than just words in the advertisement. The engine does not infer a formal auditor credential from an ISO keyword. Total industrial experience is not described as an equivalent number of years of HSE leadership; requirements still need review against exact history.

Configured weights now work. The occupational gate remains independent and cannot be bypassed by weight tuning. A maximum of 25 points is retained for occupational relevance; the six configured weights distribute the remaining 75 fit points, including employment preference. API weights must be nonnegative and total 100. Raw component evidence and the final weighted breakdown are distinguished in explanations. Derived job scores refresh at startup and after explicit profile or matching-preference changes; vacancy facts, saved flags, documents and application history are not rewritten by rescoring.

Matching no longer excludes a management role merely because its description contains `international` or `internal` (the earlier `intern` substring check was too broad). Relocation packages, visa assistance or welcoming global applicants are not treated as confirmation of visa sponsorship. Positive sponsorship now needs an explicit sponsorship statement, and `no relocation` alone does not mean no visa sponsorship.

### AI cache and usage control

The existing 64-character assessment hash now includes vacancy details, candidate facts, consent, selected model, matching preferences, policy version, API-key presence and day. No schema change is needed; legacy hashes become stale naturally. Stale assessments are hidden from job responses and the assessment endpoint until refreshed. API-key values are never part of the digest or logs.

Transient AI failures can be retried instead of being cached indefinitely. Failed attempts count toward the configured daily cap; quota-blocked local fallbacks do not count as extra provider calls. The live process's configured daily limit is honored. Unrelated, excluded or inactive vacancies are handled locally without a provider request. The AI prompt uses actual candidate history and achievements without adding a fixed 19-plant or 18-year HSE claim.

Changes to matching preferences or policy invalidate application preparation approvals, not just AI caches. Existing approved document packages are retained; affected applications require fresh review before portal preparation or submission recording.

### Vacancy freshness and feed safety

Greenhouse and Lever connectors now reject malformed responses and HTTP errors instead of turning them into apparently successful empty snapshots. Greenhouse totals are checked when supplied. Invalid posting IDs/titles/URLs or malformed snapshots preserve stored jobs.

Each source refresh is transactional. Missing jobs are marked inactive only after a successful snapshot and only when a native ATS URL proves ownership by an unambiguous configured board. Custom employer URLs and ambiguous same-company board mappings are not guessed closed. A valid empty snapshot can mark proven board jobs inactive. Jobs that reappear reactivate the same record, preserving notes, saved state and history. Changes to an existing posting, even if it becomes irrelevant, update its actual content and score rather than retaining an old high-scoring description. Notification dispatch happens after the refresh commits and cannot partially commit it.

Inactive jobs are omitted from the normal discovery list and high-match counts, but remain accessible by ID, in saved/history views and with `include_inactive=true`. Their application history is retained. Phase 4 refuses preparation of inactive vacancies.

### Tracker and frontend compatibility

The legacy tracker now requests every API page and includes inactive historical jobs. Stable ID tie-breaking and client-side ID deduplication prevent duplicate cards from pagination ties. The browser demonstration includes 121 extra synthetic history rows, proving that the last page and inactive records are rendered.

Phase 4 stage labels map to the appropriate legacy lanes rather than disappearing. Managed applications direct stage changes to the Control Center, protecting the confirmation/approval workflow. Actual match levels and Phase 4 status strings are included in TypeScript types and filters. Scoring settings explain the independent occupational gate.

## Validation actually executed

| Check | Result |
| --- | --- |
| Baseline full suite with Chromium and launcher flags | 93 passed |
| Updated full suite, same flags enabled | **125 passed**; no skipped browser/launcher test |
| Added targeted reliability cases | 32 tests covering evidence-based scores, weights, sponsorship, cache invalidation, consent, provider failure/cap behavior, feed errors/rollback, closures/reactivation, history and pagination |
| TypeScript | `npm run typecheck` passed |
| Production frontend | `npm run build` passed |
| Full synthetic Control Center workflow | Passed; no JavaScript errors |
| Tracker UI beyond 100 jobs | Last synthetic row rendered; submitted Phase 4 application visible |
| Python compilation / Git whitespace | Passed |
| Original uploaded SQLite snapshot | Byte-identical to pre-work backup; `quick_check=ok`; zero foreign-key violations |
| Snapshot counts | 235 jobs; 3 master CV records; 4 packages; 28 generated documents |

The original snapshot was opened read-only for inspection. Automated writes, migrations and browser demonstrations used temporary synthetic databases and documents. No real employer application was submitted, no recruiter message sent, no authenticated employer account accessed, and no external AI request was made by the tests. Provider behavior is mocked. No dependency was added.

## Remaining limits and user intervention

- **Mac installation:** this execution environment cannot operate the user's actual running Mac checkout. Pull the feature branch and restart the app to use the update. Because there are no dependency changes, an existing backend environment remains usable; rebuild the frontend if using production mode.
- **Approvals:** the matching policy changed. Review affected prepared applications and approve them again; document package history is retained.
- **Native notifications:** macOS notification permission/Focus behavior and launchd registration still need confirmation on the actual Mac. Portable tests exercise the logic using mocks, and the launcher lifecycle is tested on Linux.
- **Employer coverage:** only existing Greenhouse/Lever discovery connectors are present. The default employer feeds are still predominantly tech companies; no unverified industrial feed or fabricated vacancy was added.
- **Freshness:** missing custom-domain postings and ambiguous board ownership are deliberately left for manual review. There is no universal live application-page verifier, and only explicit structured/text deadline evidence is recognized.
- **Profile quality:** knowledge of a standard is not a certification. Review inherited candidate data and older application packages; the upgrade does not silently correct authoritative career history.
- **Integrations:** Workday/employer-specific forms, LinkedIn and Naukri remain manual or restricted to supported field preparation. Final submission always stays manual and requires a user-confirmed reference to be recorded.
- **Migration framework:** future column changes still require an explicit migration plan; `create_all` alone is not a general migration solution.
- **Configuration:** AI model/limit changes through the current settings endpoint remain process-level environment changes rather than durable provider configuration. This update respects the configured running value; persistent provider-settings management is a separate future improvement.
- **Tests:** legacy deprecation warnings remain. Passing checks are evidence for tested scenarios, not a claim of zero defects or complete live-provider compatibility.

## Files and next step

Added `backend/services/matching_context.py` and `backend/tests/test_stabilization.py`. Modified the existing matcher, discovery/connectors, eligibility, AI assessment and API/settings paths; tracker/API frontend helpers/types; and synthetic browser demo fixtures. The source diff and Git history identify every changed file. No databases, CV uploads, packages, credentials or runtime caches are committed.

Publish only to `feature/phase4-assisted-applications`; do not merge into main. Next prioritize verified industrial employer coverage, custom-domain freshness checks, durable provider settings and an actual Mac notification check. Keep the current architecture and the user's manual final-submission control.
