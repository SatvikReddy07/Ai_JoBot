# Repository status — 8 November 2026

The active branch is `feature/phase4-assisted-applications`; `main` remains older and has not been merged. The latest reliability work continues the existing Phases 1–4 rather than rebuilding them. See [STABILIZATION_REPORT.md](STABILIZATION_REPORT.md) for the exact audit, handover comparison, fixes, tests and limitations.

| Area | Current status |
| --- | --- |
| Phase 1–3 regression behavior | Retained and covered by the full suite |
| Phase 4 application workflow | Eligibility evidence, document selection, distinct approvals, manual confirmation, duplicate protection, immutable sent-outreach history and reminders |
| macOS / Windows | Existing launchers retained; native Mac notification display/launchd still requires an actual Mac check |
| Profile-aware scores | Implemented for runtime discovery, fallback and eligibility; no candidate credential is inferred from JD keywords |
| Configurable weights | Honored and validated; occupational gate remains independent |
| Assessment cache | Profile/model/preferences/consent/policy/day aware; stale results hidden and failures retryable within the daily cap |
| Source freshness | Successful native-board snapshots reconcile missing jobs; failures/malformed/ambiguous sources preserve records |
| Legacy tracker | Full pagination, inactive history and Phase 4 stage compatibility |
| Validation | 125 backend tests passed with browser and launcher integrations enabled; TypeScript, production build and expanded UI scenario passed |
| Existing uploaded data | Byte-identical snapshot retained; integrity and foreign keys checked |

Remaining work: verified industrial/pharma employer coverage, custom-domain freshness checks, persistent provider settings, explicit migrations for future column changes, candidate-data review and real permitted employer-form/native Mac verification. Passing tests do not establish that every live integration is supported.

No real employer submission or recruiter outreach was performed during development. Final portal submission remains manual; recording it requires an explicit user attestation and confirmation reference. Matching-policy changes require fresh application preparation approval. Jobs, documents, application history and saved state are preserved; derived match scores refresh at startup and after profile/preferences edits.
