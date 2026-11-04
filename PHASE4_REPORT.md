# HSE Career Agent — Phase 4 delivery report

Date: 4 November 2026 (revalidated before authorized GitHub publication). Base commit: `dba9013`. Branch: `feature/phase4-assisted-applications`.

## Result

The existing application has been extended with a local Application Control Center and an explicit, auditable preparation-to-manual-submission workflow. It has not been rebuilt. No real employer application, account login, recruiter message or public deployment was performed. GitHub publication is limited to the user-authorized Phase 4 source branch.

### Existing versus new

| Area | Existing at takeover | Delivered |
| --- | --- | --- |
| Phases 1–2 | Public Greenhouse/Lever discovery, matching, dashboard, CV upload/profile | Preserved; isolated regression tests and safer uploads/profile preservation |
| Phase 3 | DOCX/PDF generation, package ZIPs, versioning, package approvals, Studio | Preserved; hardcoded document claims/contact details removed; deterministic local generation |
| Phase 4 models | Application/contact/outreach/reminder models and schemas only | Integrated APIs, state transitions, approval fingerprints, audit records, Control Center |
| Eligibility | No Phase 4 service | Occupational gate, mandatory requirement evidence, unknown work rights/sponsorship, explicit user evidence reviews |
| Application preparation | No integrated control flow | Approved package and exact version selection, verified fields, mandatory question checks, user-reviewed URLs |
| Submission | No Phase 4 confirmation workflow | Final action manual; explicit user attestation plus confirmation reference required |
| Outreach | Models only | Editable recruiter/hiring-manager/TA/referral/follow-up drafts, separate approval and manual-send recording |
| Reminders | Existing high-match alerts | Configurable follow-up reminders, default seven days, duplicate suppression, Windows task setup |
| Browser assistance | Not implemented | Optional visible Chromium helper, exact input allowlist, approved uploads, no button clicks, manual fallback |

## Architecture and data changes

New FastAPI routes are grouped in `backend/app/phase4.py` under `/api/phase4`. Eligibility, portal classification and reminders have separate local services. The existing Application Studio and public discovery connectors remain in use. The Control Center is integrated into the existing navigation.

The migration is additive: it creates the previously unmaterialized Phase 4 tables (`job_applications`, `recruiter_contacts`, `recruiter_outreaches`, `follow_up_reminders`) and two new tables (`application_events`, `reminder_deliveries`). Existing table columns and user records are not rewritten. A consistent SQLite backup is created before missing tables are added. Jobs already marked Applied/Interview/Offer in the legacy tracker are protected against accidental duplicate preparation.

One application per job is enforced by SQLite. An additional locked lookup detects the same vacancy URL across discovery sources while ignoring tracking parameters. Closed or previously submitted applications are not silently reset. Application history and approval activity are retained.

Preparation approval signs the exact selected document IDs, versions and file hashes, candidate profile, vacancy details, portal URL, answers, verified fields and eligibility evidence. Changes require fresh approval before browser assistance or submission recording. Package approval alone is insufficient.

## Measured validation

| Check | Actual result |
| --- | --- |
| Full backend suite, including optional Chromium test | **78 passed**, no skipped browser test (`HSE_RUN_BROWSER_TESTS=1`) |
| Phase 3 / 3.1 compatibility QA entrypoint | **18 passed**; runs the isolated Phase 3 and matcher tests |
| Frontend TypeScript | `npm run typecheck` passed |
| Frontend production build | `npm run build` passed on Next.js **14.2.35** |
| Local mock employer browser workflow | Filled synthetic name/email and approved-file inputs; helper did not submit; simulated user click produced `MOCK-LOCAL-001`; user confirmation recorded |
| Full Control Center browser scenario | Shortlist → document selection → approval → mock portal → manual submission record → reminder → outreach draft passed; **zero JavaScript errors** |
| Data preservation | Original SQLite database is byte-for-byte identical to its pre-work backup; integrity `ok`; **235 jobs retained** |
| Additive migration test | Preserved a synthetic legacy table and marker row; backup created; integrity `ok` |
| Python syntax and whitespace | Compilation and `git diff --check` passed |
| Credential-pattern scan | Eight inherited Git commits scanned for common Gemini/GitHub/private-key patterns; no matching files found. This is a scoped scan, not an exhaustive secrets guarantee. |

The 37 existing regression tests were retained. One obsolete parser assertion was corrected: unstructured text must not result in four invented employment records. The test now requires an empty unverified employment history. The old Phase 3.1 QA script, which edited active records and inserted an invented credential, is now a compatibility entrypoint into isolated tests.

The suite emits legacy deprecation warnings, primarily naive UTC timestamps and FastAPI startup events. These are not failing tests. Windows toast rendering and Task Scheduler execution cannot be verified on this Linux host.

### Reproduce the demonstration

Install `backend/requirements-dev.txt`, install Chromium with `python -m playwright install chromium`, build the frontend, stop any existing local app, then run:

```powershell
.\backend\venv\Scripts\python.exe scripts\verify_phase4_ui.py
```

The demonstration refuses occupied ports, creates a fresh temporary synthetic database and documents, and serves the application on loopback. A fake HTTPS employer URL is fulfilled locally by the test browser; no employer traffic is sent. All final-click simulation is confined to that mock form. The separate test portal can also be run with `python scripts/mock_employer_portal.py`.

## Supported workflows and limits

- **Greenhouse / Lever:** existing public discovery; approved document preparation; manual application or optional exact-name field filling.
- **Workday / other employers:** manually verified links, package downloads, question review and confirmation tracking. No universal Workday scraper or adapter is claimed.
- **LinkedIn / Naukri:** link opening, manual application tracking and editable outreach drafts. No protected-content scraping, credential storage, connection requests or automatic sending.
- **Browser helper:** a fresh visible browser, manual login/CAPTCHA, exact host allowlist and approval recheck after login. Only supported basic input/file names are filled. Questions, complex widgets, multi-step flows and redirects need manual handling. Failure never marks an application submitted.
- **Eligibility:** conservative text screening and user-supplied evidence, not a legal/work-permit determination. Complex qualification alternatives, missing language requirements and unknown work rights remain under review. Sponsorship statements do not prove the candidate's personal eligibility.
- **Submission evidence:** a user-entered reference and explicit attestation, not independent employer/email verification.
- **Windows reminders:** run only while the user is signed in and the PC is awake; quiet hours apply. No auto-contacting recruiters.
- **Existing records:** preserved unchanged. The stored L&T role conflicts with the user's confirmed maintenance/operations Assistant Manager period through November 2016. Correct that profile explicitly and review old documents before approving them. New default-profile code uses the confirmed L&T description; it does not silently rewrite the stored profile.
- **Contact details:** no hardcoded email/phone is generated. Add and verify contact details in the document editor and application fields before approval.
- **Gemini:** optional job analysis remains. Application documents are generated locally from reviewed facts to avoid unsupported AI claims. No subscription or paid API is required.

## Security and privacy

Loopback startup is explicit for both frontend and backend. Browser origins and HTTP Host headers are restricted. CV uploads accept PDF/DOCX with generated storage names and a 10 MiB limit. CV and package download routes enforce local directory containment. Application URLs reject credentials, non-HTTPS schemes, loopback/private IPs and nonstandard ports. User verification of employer identity remains essential; URL shape alone does not establish that identity.

Passwords are neither requested nor stored. No automatic sending/submission endpoints exist. Mandatory question verification and independent application approval prevent package approval from becoming submission consent. Modified wording invalidates outreach approval. Notification content is encoded before invoking PowerShell to avoid interpreting recruiter/job text as shell commands.

Databases, personal CVs, generated documents, environment credentials, logs and runtime dependencies are excluded from the source update. Local services are intended for a trusted single-user machine; there is no multi-user authentication. Prefer a permitted personal folder outside corporate OneDrive. The update does not upload existing personal documents or data.

## Acceptance review

| Criterion | Status |
| --- | --- |
| Existing phases continue to pass regressions | Passed |
| Unrelated roles excluded from application queue | Passed |
| Unknown eligibility and mandatory gaps remain explicit | Passed |
| Approved documents and specific versions available | Passed |
| Supported form filling or manual fallback | Passed against local mock; employer-specific live behavior unverified |
| Final submission under user control | Passed |
| Duplicate prevention and retained history | Passed |
| User-confirmed submissions accurately distinguished | Passed |
| Follow-up scheduling/modification/disable | Passed; native Windows execution requires PC validation |
| No paid service required | Passed in local mode |
| Credentials and personal data excluded from update | Passed for the packaged source update |
| Critical test checks | Passed |

## Files

New: `backend/app/phase4.py`; `backend/services/{eligibility_service,portal_service,reminder_service}.py`; `backend/requirements.txt`; `backend/requirements-dev.txt`; `backend/tests/test_phase4.py`; `frontend/src/components/ApplicationControlCenter.tsx`; `pytest.ini`; `scripts/{assist_application,mock_employer_portal,run_followup_reminders,seed_phase4_demo,phase4_ui_scenario,verify_phase4_ui}.py`; `scripts/setup_local.ps1`; `scripts/setup_reminder_task.ps1`; this report.

Modified: `.gitignore`; `README.md`; `backend/app/{database,main,models,schemas}.py`; `backend/services/{cv_parser,notification_service,package_service,tailoring_service}.py`; `backend/tests/{conftest,test_phase2}.py`; frontend dependency manifests; `frontend/src/app/page.tsx`; `frontend/src/components/Sidebar.tsx`; `scripts/start_app.ps1`; `scripts/test_phase3_qa_suite.py`. The uploaded `frontend/next-env.d.ts` line endings were normalized without changing its declarations.

## Recommended next steps

Update the Windows feature branch from GitHub, run Windows setup, review/correct the existing candidate profile and regenerate any old packages. Check one local toast reminder and one permitted portal in manual mode before enabling optional field filling. Publication to `feature/phase4-assisted-applications` was authorized on 4 November; merging into main is outside this update. The exact resulting commit is available in the branch history. The previously delivered ZIP is an earlier snapshot.

## Pre-push review — 4 November 2026

Ten additional regression cases now cover specific mandatory qualifications, employer/location/employment-type changes, sent-message history and empty document contact defaults. Mandatory requirement keywords never establish a full qualification by themselves. Application approval includes all relevant vacancy identity and location fields. Sent outreach is immutable history, with the exact wording retained in the audit log; a new message requires a new draft. Remaining placeholder cover-letter contact defaults were removed. The dashboard disables editing or reapproving already-sent drafts.

Fresh verification: 78 backend tests passed with the optional local Chromium test enabled; TypeScript and production build passed; the isolated dashboard workflow passed with zero JavaScript errors. The original database remains byte-identical to its pre-work backup (235 jobs, integrity `ok`). No credentials, personal CV files, databases or generated application packages are included in the source update. This validation establishes the tested behavior; it cannot guarantee absence of all defects or verify Windows-specific notifications on this Linux host.
