# Repository assessment — 8 November 2026

## Scope and current stage

Reviewed GitHub `SatvikReddy07/Ai_JoBot`, particularly Phase 4 commit `4489d78cf7151993a33d3a6073c022ab63b313c9`, and tested the subsequent Mac portability update. GitHub `main` remains at the older `3d8b0a3`; the active development branch is `feature/phase4-assisted-applications`. Clone/pull that branch to get the current features. No merge into main is part of this work.

The app is an existing local career assistant: Next.js 14 / React / TypeScript / Tailwind frontend, FastAPI / SQLAlchemy / Pydantic backend, and SQLite persistence. Optional Gemini analysis supplements deterministic matching. DOCX and PDF application documents are generated locally. This is a single-user local application, not a public multi-user service.

## What is implemented

| Area | Status and limits |
| --- | --- |
| Public job discovery | Greenhouse and Lever connectors, employer configuration, deduplication, saved jobs, history |
| Matching | Occupational gate, explainable fit scores, sponsorship-text detection; excludes unrelated software/sales titles |
| Profile and CV | PDF/DOCX text extraction, editable profile; uploads preserve existing confirmed facts |
| Application Studio | Local CV and cover-letter generation, DOCX/PDF/ZIP downloads, versions and package approval |
| Control Center | Eligibility evidence review, document selection, questions, independent approval, manual submission confirmation |
| Tracking | Duplicate prevention, state transitions, audit history, recruiter drafts and manual-send records |
| Portals | Manual workflows and optional allowlisted field assistance; no universal employer/Workday automation |
| LinkedIn / Naukri | Links, drafts and manual tracking; no protected scraping or automatic sending |
| Notifications | Windows toast and Mac scripting dispatch; explicit OS-specific reminder scheduling |
| Mac daily use | Setup/start/stop `.command` files, readiness checks, logs, process ownership and duplicate-launch protection |

## Findings still requiring work

1. **Discovery coverage is narrow.** The seven default feeds are Canva, Stripe, Deliveroo, GitLab, Gusto, Atlassian and Miro. They are predominantly tech employers. A successful search is not evidence of broad manufacturing/pharma/industrial HSE market coverage. Additional employer feeds must be verified before adding them; no invented live vacancy claims.
2. **Suitability is not fully profile-driven.** `matcher.py` scores job terms against fixed maps. Its educational rationale can say a candidate satisfies engineering/auditor requirements based on words in the vacancy, without proving those facts in the candidate profile. Phase 4 eligibility separately requires review of mandatory qualifications, but the displayed legacy fit rationale needs improvement.
3. **Configured weights are unused.** Discovery reads and passes `scoring_weights`, but `HSEJobMatcher.evaluate` does not use its `weights` parameter. Editing those settings currently does not change the fixed scoring dimensions.
4. **AI caches can be stale after profile edits.** `analyze_job_with_ai` builds its cache hash from job title/location/description and returns a matching cache entry before recalculating against the current profile. Profile, model and matching-policy changes should participate in cache identity.
5. **Closed vacancy detection is incomplete.** Discovery sets retrieved jobs active, but does not deactivate missing/closed jobs after a successful feed refresh. Eligibility only recognizes explicitly supplied ISO-format deadlines; other dates remain for manual review. Last-seen verification and source-backed expiry checks should precede applications.
6. **Legacy tracker pagination is incomplete.** `loadTrackerJobs` requests page 1 with 100 jobs and does not fetch remaining pages. Larger databases can therefore hide jobs in that older view. The Phase 4 application list is a separate API.
7. **Legacy candidate data needs user review.** Default profile seeds and older packages are preserved rather than silently rewritten. Knowledge of ISO standards is not proof of a formal certification. Verify titles, dates, qualifications, achievements and contact details before approving any package.
8. **Portability is tested within limits.** The backend and web frontend run on Unix, and the Mac launcher lifecycle is exercised on Linux. Native macOS notification display and launchd registration require a real Mac and its notification permissions. Existing Windows reminder code remains available. Manually started services are not automatically stopped by the new launcher.

These are source-backed findings, not a claim that every runtime defect has been discovered. Passing tests establish the scenarios tested, not absence of all bugs.

## Validation of this update

- **93 backend tests passed**, with both `HSE_RUN_BROWSER_TESTS=1` and `HSE_RUN_LAUNCHER_TESTS=1` enabled.
- Tests cover Windows dispatch compatibility; safe Mac notification argument handling; launchd plist paths with spaces; install/remove ownership; authenticated shutdown; service readiness; duplicate launch rejection; actual start/stop of isolated services; Phase 1–4 regressions; and the synthetic mock employer workflow.
- TypeScript check and Next.js production build passed.
- The separate synthetic dashboard workflow passed with zero JavaScript errors.
- Bash syntax, Python compilation and Git whitespace checks passed.
- The original source snapshot's database remains outside Git and is not migrated or copied to the user's Mac by this update. Tests use disposable data.
- Native macOS display/registration calls are mocked here; they are not reported as tested on the user's computer.

The first launcher integration test exposed unreliable PID/process inspection, and a later test exposed TIME_WAIT port-reuse behavior. Shutdown now uses a random authenticated loopback control channel with a mode-0600 local state file. The launcher stops only its own child process groups, refuses occupied ports, and reuses safe socket bind semantics for restarts. No process-discovery dependency is needed for stop.

## Recommended next milestone

Prioritize reliable results over additional submission automation: fix profile-aware matching and cache invalidation first, then honor configurable weights, improve verified industrial employer coverage, deactivate closed jobs and paginate the legacy tracker. Keep final employer submission manual. Mac notification permissions should be checked once on the user's already-running Mac installation after pulling the feature branch.
