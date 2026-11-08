# HSE Career Agent — Phase 4

Private Windows and macOS application for discovering HSE vacancies, reviewing fit, preparing truthful application documents and tracking manual submissions. No paid service is required. Gemini job matching is optional; document generation uses reviewed profile facts locally.

## macOS setup and daily use

Phase 4 is on `feature/phase4-assisted-applications`. After pulling that branch:

```bash
# First-time setup or dependency update (existing data is preserved):
./SETUP_HSE_AGENT.command
# Start both services, check readiness, then open the dashboard:
./START_HSE_AGENT.command
# Stop only the processes created by this launcher:
./STOP_HSE_AGENT.command
```

The `.command` files can also be opened from Finder. Keep the startup Terminal window open while using the app; Control+C stops both managed services. If your existing manually launched app already occupies port 3000 or 8000, the launcher reports that and leaves it running. Stop it in its original terminal before using the new launcher. Logs are in `data/logs/backend.log` and `data/logs/frontend.log` (or your `HSE_DATA_DIR`). The frontend must be built first; the already-running `npm run dev` workflow remains available.

Use Python 3.12 to create `backend/venv` and a compatible installed Node.js. Setup uses an existing Mac virtual environment if present. A Windows virtual environment cannot be reused on Mac.

### Mac follow-up reminders

```bash
# Enable this project's user-only LaunchAgent (no sudo):
./SETUP_REMINDERS.command
# Disable it:
backend/venv/bin/python scripts/macos_reminders.py remove
```

Reminders check every 15 minutes while signed in and awake, with the same quiet hours and duplicate suppression as Windows. The app uses native macOS scripting notifications; macOS notification permissions and Focus settings may suppress display. Installation is explicit and is not performed by ordinary application startup. After moving the repository, remove the old task before moving it, then install it again at the new path. Notification dispatch and launchd registration require final verification on a real Mac; portable tests mock these system calls.

The clone includes source, not your old Windows jobs/CVs/packages. If you want those records, stop both copies, back up and copy the existing `data` directory privately; preserve `hse_career.db`. Old absolute Windows document paths may need package regeneration. This update does not transfer or rewrite personal records.

## Windows setup

Install Python 3.12 and Node.js 20 or 22 LTS. In the existing project folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_local.ps1
.\START_HSE_AGENT.bat
```

Frontend: http://127.0.0.1:3000. Backend: http://127.0.0.1:8000. API documentation: http://127.0.0.1:8000/docs.
Both startup commands bind to loopback. Setup installs dependencies and builds the frontend; it does not replace the database. For a personal installation use a permitted directory such as `C:\HSE-Career-Agent` outside corporate OneDrive. Copy the complete existing `data` folder when moving; retain an offline backup. Older absolute document paths require package regeneration in Application Studio.

## Application Control Center

1. Review **My Career Profile**. Correct old records explicitly, especially the L&T maintenance/operations period ending November 2016. Uploading a CV extracts its text and preserves confirmed profile fields; extraction does not verify credentials.
2. Open **Application Control Center**. Filter the suitable jobs queue by country, employer, minimum score, eligibility, sponsorship, stage and update date. Ranking uses the current occupational matcher rather than trusting old stored scores.
3. Review requirement evidence and unknowns. Provide source-backed user confirmation where appropriate. Unknown work authorization or sponsorship never becomes confirmed automatically. Confirmed mandatory gaps exclude preparation.
4. Shortlist a vacancy. Use **Application Studio** to generate, edit, download and approve the CV/cover-letter package. Old packages remain preserved and must be reviewed for factual accuracy.
5. Return to the Control Center, select the approved package and exact document versions, verify the employer URL, and review the candidate facts.
6. Enter verified contact fields and the employer's application questions. Unknown answers stay blank. Every mandatory answer must be reviewed before approval.
7. Save preparation and approve this specific application. Package approval and application preparation approval are separate. A document-version, file-content, profile, answer or eligibility change invalidates the stored approval digest.
8. Open the portal, sign in manually, review/copy fields and upload documents. Final submission is manual. Merely opening a portal never records a submission.
9. Record a confirmation number or confirmation-email reference and explicitly attest that you submitted manually. This is user-recorded evidence, not independently verified employer acceptance.
10. Track follow-ups, interviews, rejection, offers or withdrawal. One application per vacancy is enforced by SQLite and the API. Closed/submitted applications cannot silently overwrite their document selections.

## Portal support

| Portal | Actual support |
| --- | --- |
| Greenhouse / Lever | Existing public discovery connectors; manual application preparation; optional allowlisted form helper |
| Workday / employer portals | Verified link opening, approved downloads, questions/checklist and manual tracking; no new public-feed crawler |
| LinkedIn / Naukri | Link-based preparation, editable outreach/referral drafts and manual tracking; no authenticated scraping or automated sending |

Employer identity and official URLs require user verification. No passwords are stored. CAPTCHAs, account access and final submission remain manual. The browser helper does not click buttons and does not attempt to identify every employer-specific question.

### Optional visible browser helper

```powershell
.\backend\venv\Scripts\python.exe -m pip install playwright==1.56.0
.\backend\venv\Scripts\python.exe -m playwright install chromium
# First approve and start the specific application in the Control Center.
.\backend\venv\Scripts\python.exe scripts\assist_application.py 1 --allow-host jobs.lever.co
# Explicitly opt into filling a supported form in a fresh visible session:
.\backend\venv\Scripts\python.exe scripts\assist_application.py 1 --allow-host jobs.lever.co --fill
```

The helper fills unique visible editable inputs with exact allowlisted names (`name`, `full_name`, `email`, `phone`, `location`, `company`, `current_role`) and file inputs named `cv` / `cover_letter`. It revalidates approval after manual login. Unsupported fields, redirects, authentication challenges or browser errors require the manual checklist. Passwords, demographic answers and work rights are never automatically filled.

### Local follow-up reminders

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_reminder_task.ps1
# Disable the Windows task:
powershell -ExecutionPolicy Bypass -File .\scripts\setup_reminder_task.ps1 -Remove
```

An interactive, least-privilege Windows task checks every 15 minutes while signed in and awake. Quiet hours: 22:00–07:00 local time. A successful reminder is logged once; failed notifications can retry. Default follow-up is seven calendar days after confirmed manual submission. Dates can be changed, completed or disabled in the dashboard. No recruiter email or message is sent.

## Storage, migration and privacy

- Default SQLite path: `data/hse_career.db`. `HSE_DATA_DIR` can isolate a test/demo installation.
- Phase 4 adds `job_applications`, `recruiter_contacts`, `recruiter_outreaches`, `follow_up_reminders`, `application_events` and `reminder_deliveries`. Existing tables and records are retained. An existing database is backed up before missing tables are created.
- `application_events` retains preparation approvals, stage changes, outreach activity and reminder changes. Profile/document signatures and file hashes detect stale approvals.
- CV uploads accept PDF/DOCX up to 10 MiB with generated storage names. Package download paths are confined to the packages directory. Browser origins and HTTP hosts are restricted for local use.
- Personal CVs, databases, generated packages, credentials, logs and runtime caches are excluded from Git. The app has no user-login authentication and is intended for a trusted single-user machine only.
- Optional Gemini job analysis can send structured profile/job data only after consent; generated application documents remain deterministic and local. Free-tier availability depends on the configured provider account; leave the API key unset for an entirely local workflow.
- Existing data may contain inaccurate legacy baseline claims. Review it; the upgrade deliberately does not silently rewrite authoritative user records or old packages.

## Verification

```powershell
.\backend\venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
.\backend\venv\Scripts\python.exe -m pytest backend\tests -q
cd frontend
npm run typecheck
npm run build
```

To run the complete synthetic UI demonstration after building, stop the local app and run `python scripts/verify_phase4_ui.py`. This uses disposable synthetic records and a locally intercepted fake employer page. Set `HSE_RUN_BROWSER_TESTS=1` to include the optional mock-portal test in pytest.

Tests use a temporary data directory and an in-memory SQLite database. The matcher regression checks include the unrelated Stripe/software role. The updated CV parsing test rejects fabricated employers rather than requiring hardcoded history.

For a synthetic employer portal, run `python scripts/mock_employer_portal.py` and open http://127.0.0.1:8765. This is a local test form, not a real vacancy or employer. See `PHASE4_REPORT.md` for measured results and remaining platform limitations.

## Source layout

```text
backend/
  app/         Existing API/models/schemas plus phase4.py router
  connectors/  Existing Greenhouse and Lever public discovery
  services/    Matching, parsing, documents, eligibility, portals, reminders
  tests/       Phase 1–4 regression and integration tests
frontend/
  src/app/             Existing Next.js application
  src/components/      Application Studio, Control Center, profile, tracker
  src/lib/             Existing typed API client
scripts/               Setup/startup, browser helper, reminders, mock portal
```
