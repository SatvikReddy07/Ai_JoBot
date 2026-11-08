# HSE Career Agent — verified project memory

Verified: 8 November 2026. Repository: https://github.com/SatvikReddy07/Ai_JoBot

Treat this file as a verified checkpoint, not a substitute for inspecting the current branch and working tree. The user's Mac checkout is already configured and running; this execution environment cannot directly inspect or operate that Mac.

## Branch and publication checkpoint

- Active development branch: `feature/phase4-assisted-applications`.
- Verified reliability commit: `8078e4c50d4146ccf2bee7ee93322bb2545c46bd`.
- Reliability source tree: `33cc49802c9566e2a0273aea0077a3f11b7317a8`.
- Previous Mac support commit: `23b50af32936f8b857251e57f092d6b4ae9cb3d3`.
- Earlier Phase 4 implementation commit: `4489d78cf7151993a33d3a6073c022ab63b313c9`.
- `main` remained at `3d8b0a326f4405a4ce3fc77ea02627f97b06d7b3`; merging into main requires explicit user approval.
- The reliability commit is already on GitHub; do not duplicate or replay it. This memory is a separate documentation follow-up. Find this file's containing commit with `git log -1 -- PROJECT_MEMORY.md`.
- Previous execution-copy commit IDs differ from GitHub-created commits, but the source tree was verified identical before publication. Do not force-push one history over the other.

## Goal and constraints

Continue the existing Phases 1–4 as a private personal HSE career assistant. Use the current repository as technical source of truth and handovers as history. Preserve SQLite records, career facts, CVs, application packages, approvals and history. Keep macOS and Windows support. Default to local processing and no mandatory paid dependencies. Paid services require explicit approval. Do not rebuild the application, fabricate vacancies or candidate credentials, bypass access restrictions, automatically send recruiter messages or submit applications without the specific authorization required by the workflow.

Final employer submission is manual in the current release. An application may be recorded as submitted only after explicit user attestation and a confirmation number/email reference. Opening or filling a portal is never submission confirmation. Tests used mock confirmations; no real employer submission was made.

## Architecture and implemented behavior

Next.js 14 / React / TypeScript / Tailwind frontend, FastAPI / Pydantic / SQLAlchemy backend, local SQLite, optional consent-controlled Gemini matching, deterministic local DOCX/PDF generation and application ZIPs.

- Phase 1: Greenhouse and Lever public feeds, employer configuration, discovery, relevance gating, scores, saved jobs, search history and tracking.
- Phase 2: PDF/DOCX extraction and editable profile. CV upload preserves confirmed profile fields. Optional matching has consent, caching, quotas and local fallback.
- Phase 3: Application Studio, local CV/cover-letter generation, DOCX/PDF/ZIP downloads, revision history and package approval.
- Phase 4: evidence-based eligibility review, Application Control Center, exact approved document selection, mandatory-question verification, independent preparation approval, duplicate protection, state transitions, confirmation recording, recruiter drafts/manual-send records, audit history and follow-up reminders.
- Portal helper: optional visible Playwright session; unique allowlisted input names and approved document uploads; manual login/CAPTCHA; no final-action clicks. Generic/unrecognized forms fall back to manual preparation.
- Mac: executable setup/start/stop `.command` files, readiness checks, logs, duplicate-launch protection, authenticated local shutdown and user-scoped launchd reminders. Existing Windows scripts remain.

Candidate facts must come from the confirmed profile/master CV. Preserve the user's correction that maintenance and operations continued through the L&T Assistant Manager period ending November 2016; do not label all industrial experience as HSE leadership. Knowledge of ISO standards alone is not proof of a formal certification. Existing candidate records and older packages still require user review.

## Reliability fixes verified in 8078e4c

1. Shared profile/preferences input for discovery, fallback matching and eligibility. Technical, industry and academic credits require profile evidence; exact qualifications, licenses and work rights still require review.
2. Configured scoring weights now affect fit. Occupational relevance/gating remains independent: up to 25 relevance points plus 75 fit points distributed by validated weights. Unrelated roles remain capped/excluded.
3. Derived scores refresh on startup and after explicit profile/preferences edits. Authoritative vacancy facts, saved flags, documents and application history are preserved.
4. AI cache identity includes the vacancy, profile, model, preferences, consent, policy, key presence and day. Stale results are hidden until refreshed. Failed AI attempts count against the running daily cap; transient failures remain retryable within that cap. No tests contacted a real AI provider.
5. Relocation benefits/global-applicant wording do not establish visa sponsorship. `international` / `internal` do not trigger the former `intern` substring exclusion.
6. Feed snapshots are validated and applied transactionally. Failed/malformed responses preserve records. Successful unambiguous native-board snapshots can mark missing jobs inactive without deleting them; reappearance reactivates the same saved row. Custom/ambiguous URLs are not guessed closed.
7. The legacy tracker loads every page, includes inactive history and maps Phase 4 stages to visible lanes. Managed applications use the Control Center for state changes.
8. Matching-policy/preferences changes expire preparation approval. Existing document packages and historical approval records are retained; a fresh application review is needed.

## Final diff review

Compared remote `23b50af..8078e4c`: one commit, 24 changed files, 780 added / 321 removed lines, no merge and no unrelated change identified. Files concern matching/context, cache and API validation, transactional discovery/connectors, tracker/types/filters, regression tests, isolated synthetic UI fixtures and status/report documentation. The original framework, package manifests, dependency lists, database model definitions and Windows/Mac launchers were not replaced in that reliability commit. The larger discovery diff is a transactional refresh refactor tied to failure/closure preservation.

The working tree was clean after the reliability commit. Git whitespace and Python compilation checks passed. No `data/` files, environment secrets, personal CVs, generated packages, dependency directories or runtime caches were staged or published. This memory-only follow-up adds no application behavior or schema change.

## Tests and data evidence

- Full suite: **125 passed**, with `HSE_RUN_BROWSER_TESTS=1` and `HSE_RUN_LAUNCHER_TESTS=1`; no skipped browser/launcher integration.
- Frontend: `npm run typecheck` and `npm run build` passed.
- Full local browser demonstration: shortlist → eligibility/document review → independent approval → local mock portal → simulated user's final click → mock confirmation recording → follow-up reminder → outreach draft → legacy tracker beyond 100 rows. Zero JavaScript errors. This is a synthetic end-to-end test, not a live employer certification.
- Mocked tests cover provider behavior, notification dispatch and launchd configuration. Real Unix service start/duplicate rejection/stop was tested on Linux.
- Uploaded original SQLite snapshot stayed byte-identical to its pre-work backup: 235 jobs, 3 master CV records, 4 packages and 28 generated documents; `PRAGMA quick_check` returned `ok`; zero foreign-key violations.
- Those counts describe the uploaded snapshot, not the user's current Mac database. Git excludes that database; its contents were not read remotely from the Mac.
- No new table or column is needed for this update. Existing startup schema initialization backs up an existing database before creating missing tables. There is no general versioned/Alembic column-migration framework; plan one before future structural changes.
- Legacy deprecation warnings remain. Passing tests do not guarantee absence of all defects.

## Working end-to-end versus still unverified

| Function | Verified end-to-end scope | Remaining verification/implementation |
| --- | --- | --- |
| Local app/API/database/UI | Automated Unix start/readiness/duplicate protection/stop; temporary persistence and migration tests | Actual Mac checkout restart and data continuity |
| Discovery and freshness | Mocked complete/empty/failed/malformed feeds; rollback, closures and reactivation | Live Greenhouse/Lever feed smoke check; broader verified industrial feeds; custom-domain freshness |
| Matching and eligibility | Profile/weights/unknowns/domain gates and settings/API integration | Acceptance review using the actual master CV and representative employer requirements |
| Document preparation and approval | Real local DOCX/PDF/ZIP generation; version selection, approval and invalidation | Human review of actual candidate facts, layout, contacts and ATS upload acceptance |
| Application Control Center/tracker | Full local browser workflow, more than 100 records and managed stages | Actual Mac usability acceptance |
| Employer form assistance | Real Chromium against a local mock form, fields and uploads; failure/manual fallback | Permitted live employer form preparation; provider-specific complex widgets/steps. No universal Workday adapter |
| Submission records | Mandatory user confirmation/reference, safe state transitions and retained history | One user-approved real application pilot; independent email/receipt ingestion is not implemented |
| Recruiter outreach | Editable drafts, separate approval, immutable manual-send history | User checks a real message/channel manually. No automatic sending is implemented or required |
| Reminders | Scheduling data, seven-day default, reschedule/disable, quiet hours and deduplication; platform calls mocked | Native macOS display/Focus permissions and actual launchd run; native Windows Task Scheduler/toast check |
| Security/data safety | Localhost/URL/upload/download controls, consent/approval tests and preserved uploaded data | Backup/restore and acceptance check against the user's current Mac data |

## Phase 4 completion estimate: 80/100

This is an engineering acceptance estimate using the explicit weighted rubric below, not a test-pass percentage, live-provider certification or hiring-success prediction. Credits are deliberately withheld for work that exists only in mocks or needs actual user/device/provider acceptance. Phase 4 can accept manual fallback; universal employer automation is not its definition of completion.

| Acceptance area | Weight | Verified credit | Remaining credit depends on |
| --- | ---: | ---: | --- |
| Eligibility and profile-aware matching | 15 | 12 | Real CV/JD acceptance and work-rights review |
| Documents, versions and approval | 15 | 14 | Actual candidate package/ATS acceptance |
| Control Center and tracker | 10 | 10 | Tested local workflow complete within current scope |
| Duplicate protection, state/history | 10 | 10 | Tested within current scope |
| Confirmed manual submission records | 10 | 9 | Real user-approved pilot confirmation |
| Supported browser assistance/fallback | 15 | 6 | Live permitted form validation and provider-specific preparation where needed |
| Recruiter outreach drafts/history | 5 | 4 | Manual live-channel acceptance |
| Reminders and platform portability | 10 | 6 | Native Mac/Windows notification and scheduler verification |
| Privacy, data preservation and recovery | 10 | 9 | Actual Mac backup/restore/upgrade acceptance |
| **Total** | **100** | **80** | **20 points remain under this rubric** |

Before Phase 5: (1) update/restart the actual Mac with a verified backup; (2) review actual profile/CV and representative job matches; (3) verify native reminders; (4) test permitted live form preparation without automatic final submission, or explicitly accept manual fallback for that portal; (5) complete one separately authorized real application pilot and record genuine confirmation; (6) validate restore/data continuity and document acceptance criteria. Implement provider-specific preparation only where these checks reveal a real need. Improving industrial employer coverage, custom-domain freshness, durable provider settings and a future migration framework remain explicitly tracked; do not silently count them as completed.

Do not begin Phase 5 or merge into main merely because a percentage was stated. Obtain the user's acceptance of the remaining Phase 4 scope and any new Phase 5 objective.

## Exact Mac update and restart procedure

Run in the already-cloned repository root. Use the existing Mac Python environment; do not clone again, recreate the database, copy a sample `data` directory or run the synthetic seeding script on personal data.

1. Stop the running app. If started by the managed launcher, use `./STOP_HSE_AGENT.command` and wait for its startup terminal to finish. If started manually, press Control+C in both the backend and frontend terminals. The managed stop intentionally does not terminate manually started services.
2. If you use `HSE_DATA_DIR`, export the same **absolute path** in this terminal before backup and restart. Otherwise the database is `data/hse_career.db`. Keep the existing environment configuration.
3. Make and verify a consistent backup with the existing interpreter:

```bash
backend/venv/bin/python - <<'PY'
import os
import sqlite3
from datetime import datetime
from pathlib import Path
folder = Path(os.environ.get("HSE_DATA_DIR", "data")).expanduser().resolve()
db = folder / "hse_career.db"
if not db.is_file():
    raise SystemExit("Database not found at " + str(db) + "; locate the running app's data directory before proceeding.")
backup = folder / ("hse_career_manual_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".db")
with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as source, sqlite3.connect(backup) as target:
    source.backup(target)
    if target.execute("PRAGMA quick_check").fetchone()[0] != "ok":
        raise SystemExit("Backup integrity check failed; do not update yet.")
print("Verified backup:", backup)
PY
```

4. Run `git status --short`. If it shows local source changes, preserve/review them first; do not use reset/clean/force-pull. Then update the feature branch:

```bash
git switch feature/phase4-assisted-applications
git pull --ff-only origin feature/phase4-assisted-applications
(cd frontend && npm run build)
./START_HSE_AGENT.command
```

No new dependencies are required for the reliability/documentation updates. An existing working Mac environment and installed frontend dependencies can be reused. `git pull` updates tracked source; the existing ignored database and uploaded/generated files remain in place. The backend deliberately refreshes derived match scores on startup but does not replace the database or remove history. Old preparation approvals may need a fresh review because the policy changed.

5. Open `http://127.0.0.1:8000/health` (expected app version `4.1.0`, Phase 4) and `http://127.0.0.1:3000`. Check saved jobs, career profile, old packages and application history. Logs: `data/logs/backend.log` and `frontend.log`, or the corresponding directory under `HSE_DATA_DIR`.
6. If needed, enable Mac reminders explicitly using `./SETUP_REMINDERS.command`; allow native notifications when prompted. A reminder record in the dashboard alone does not prove a native notification appeared.
7. To validate backup recoverability, use a separate disposable data directory/SQLite connection and compare table counts and integrity. Do not restore over the active database as an update step. Keep the verified backup for recovery.

If the pull refuses because of local commits/changes or divergence, stop and report `git status` and `git log -5 --oneline`; preserve both histories. Do not force-push, overwrite local data or merge into main.

## Next maintainer instructions

Inspect the current remote/local branch before editing. Reuse these verified tests rather than restarting Phase 1. Run targeted tests for meaningful changes, then the full required checks. Use synthetic data for automated external-workflow tests. Label live integration limits honestly, record actual confirmations only, and publish tested work to the existing feature branch when authorized. See `STABILIZATION_REPORT.md`, `PROJECT_STATUS.md` and `README.md` for implementation details.
