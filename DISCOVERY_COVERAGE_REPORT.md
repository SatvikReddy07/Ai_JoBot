# Discovery coverage repair — 2026-11-08

## Observed problem and verified cause

The fresh Mac installation fetched 1,296 postings from four working legacy boards but accepted zero HSE vacancies. The Canva/Greenhouse, Atlassian/Lever and Miro/Lever URLs returned 404. Direct public-feed checks reproduced those 404s. The four working feeds were dominated by technology roles: Stripe had no HSE-titled vacancy in the inspected snapshot; Deliveroo's Trust & Safety role concerned fraud; the health-related GitLab and Gusto titles were unrelated. A successful fetch is not evidence of useful HSE coverage.

## Changes

- Seven verified public employer feeds replace the old default list for fresh installations.
- The complete original seven-board catalog is upgraded once: the three unavailable default feeds are disabled and retained, seven new feeds are added, and the four working old sources remain. This gives 11 enabled sources in an unchanged legacy installation. No job, document, profile or application history is deleted.
- Existing disabled choices and custom feeds are preserved. A custom-only/partially replaced catalog is not silently changed. The retained retirement marker makes the upgrade idempotent and respects subsequent deliberate enable/delete actions. A user who changes the old catalog can add the new feeds under Settings → Configured Employer Career Feeds.
- Encoded Greenhouse HTML is decoded before tag stripping. Script/style content is removed. Actual responsibilities remain readable instead of being hidden behind markup within evidence windows.
- Discovery uses the occupational classifier rather than a separate 1,200-character description gate. Explicit environmental management, process safety, OHS/WHS/HSSE and Health, Safety & Environment titles are recognised.
- Incidental policy text or reporting to an HSE manager does not make a scientist, electrician, general manager or legal role HSE work. Trust & Safety, functional/system safety and environmental product testing remain excluded unless the title separately establishes occupational HSE scope. PSM/HAZOP/loss-prevention titles remain supported.
- The title gate is conservative: unusual titles without explicit HSE/environmental/process-safety scope can be missed. Review original requirements; do not relax the gate merely to inflate the vacancy count.
- Country recognition includes explicit Canada/US/Nordic names. Unknown/remote/ambiguous locations stay uncertain. Native EU Greenhouse ownership supports safe closure/reactivation by exact board token.
- Matching policy is `profile-matching-v3`; stale AI results/preparation approvals require refresh/review. Old packages/history stay intact.
- Employer settings display last feed result and label raw counts as Postings in Feed. Search History distinguishes Partial, Failed and Running.

## Live public-feed audit

The following public endpoints returned valid snapshots on 2026-11-08. Counts are a point-in-time observation, not a promise of continued availability or candidate suitability.

| Employer | Platform/token | Fetched | HSE accepted |
| --- | --- | ---: | ---: |
| AcuTech Group, Inc. | greenhouse / acutechgroupinc | 10 | 7 |
| Isar Aerospace SE | greenhouse / isaraerospace | 141 | 5 |
| Agile Robots SE | greenhouse / agilerobotsse | 73 | 1 |
| Anduril Industries | greenhouse / andurilindustries | 2600 | 5 |
| EverOn Data Center Services | lever / everondcs | 92 | 2 |
| Artis BioSolutions | lever / landmarkbio | 9 | 1 |
| Zero Carbon Systems | lever / zerocarbonsystems | 3 | 1 |
| **Total** | **7 successful feeds** | **2928** | **22** |

Public source links:

- https://job-boards.greenhouse.io/acutechgroupinc
- https://job-boards.greenhouse.io/isaraerospace
- https://job-boards.greenhouse.io/agilerobotsse
- https://job-boards.greenhouse.io/andurilindustries
- https://jobs.lever.co/everondcs
- https://jobs.lever.co/landmarkbio
- https://jobs.lever.co/zerocarbonsystems

Examples present in the audited snapshots: AcuTech Process Safety Engineers & Senior Process Safety Consultants in Navi Mumbai, Principal / Sr. Principal Process Safety Consultant in Singapore; Isar's Manager Health, Safety & Environment in Germany; Anduril's EHS Manager in Sydney. These require individual eligibility checks, including qualifications, language, work rights, export controls and sponsorship. Many added vacancies are in the United States and may not suit the candidate. Do not treat them as confirmed eligible or sponsored.

The live audit reads public jobs only, without sign-in, candidate data, messages or submission. Reproduce it from the root with:

```bash
backend/venv/bin/python scripts/audit_public_feeds.py
```

It uses a disposable data directory, performs no application writes, prints fetched/excluded/unrelated/accepted counts and accepted public titles/URLs, and exits nonzero when a feed fails. No Gemini key or paid API is required. This sandbox needed its inherited SOCKS proxy unset to use its available HTTP proxy; that is an execution-environment setting, not an app dependency or an instruction to change a Mac's proxy.

## Validation

- Backend: **163 passed**, browser and launcher integration enabled; no skipped tests.
- Added 37 synthetic regression cases for catalog upgrade/preservation/idempotence, explicit domain filtering, incidental-policy rejection, HTML evidence and locations/native EU ownership.
- Frontend TypeScript check and production build passed.
- Full synthetic browser demonstration passed: approvals, mock employer portal, manual mock-confirmation record, outreach and tracker pagination; zero JavaScript errors. No real employer application was tested or submitted.
- Replayed the fetched public snapshots through the real connectors and discovery service into isolated synthetic SQLite: 7 successful boards, 2,928 fetched, 22 new job rows, including India and Singapore process-safety records. SQLite integrity `ok`, no foreign-key violations.
- Six pre-existing SQLite files in the workspace remained byte-identical to their pre-validation fingerprints. The current database integrity was `ok` with zero foreign-key violations. This does not assert access to the user's current Mac database.
- No schema, package/dependency or credential change. Only feed configuration records and derived scores/approvals change on the real upgrade.
- Existing deprecation warnings remain; passing tests do not prove universal live-provider compatibility.

## Mac upgrade

Stop the app first. Back up the entire current data directory (CVs included), then pull the feature branch with `--ff-only`, rebuild the frontend and restart using the existing launchers. No rerun of setup or CV upload is needed. In Settings, check the new sources and disabled retired records, then Search Jobs Now. Actual counts may vary. The dashboard can show no High Matches even when discovery has jobs: match quality and eligibility remain separate checks.

## Remaining limits

This is selected public Greenhouse/Lever coverage, not a whole-market search. Sanofi, Cargill, BASF, Schneider and other unsupported portals have not been added as guessed ATS tokens. India/Singapore coverage is improved but narrow. Native reminders, actual candidate-package acceptance and separately approved live portal preparation/application pilots remain open Phase 4 acceptance work. Final submission stays manual. Main is not merged.
