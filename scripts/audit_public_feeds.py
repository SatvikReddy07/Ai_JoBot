"""Read-only live public-feed audit; never loads candidate data or writes app records.

Run from the repository root: backend/venv/bin/python scripts/audit_public_feeds.py
Availability changes; an accepted posting is not a finding of candidate eligibility.
"""
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path


async def audit():
    from backend.connectors.greenhouse import GreenhouseConnector
    from backend.connectors.lever import LeverConnector
    from backend.services.discovery import DEFAULT_BOARDS, is_hse_relevant
    from backend.services.matcher import HSEJobMatcher
    matcher = HSEJobMatcher()
    results = []
    for board in DEFAULT_BOARDS:
        connector = {'greenhouse': GreenhouseConnector, 'lever': LeverConnector}[board['platform']](
            board_token=board['board_token'], company_name=board['company_name'])
        entry = {'company': board['company_name'], 'platform': board['platform'], 'token': board['board_token']}
        try:
            jobs = await connector.fetch_jobs()
            accepted = []
            excluded = unrelated = 0
            for job in jobs:
                if matcher.is_excluded(job.title, job.description, job.employment_type)[0]:
                    excluded += 1
                elif not is_hse_relevant(job.title, job.description):
                    unrelated += 1
                else:
                    accepted.append({'title': job.title, 'location': job.location, 'url': job.url})
            entry.update(status='success', fetched=len(jobs), excluded=excluded, unrelated=unrelated, accepted=accepted)
        except Exception as exc:
            entry.update(status='failed', error=str(exc))
        results.append(entry)
        print(json.dumps(entry), flush=True)
    return 1 if any(row['status'] == 'failed' for row in results) else 0


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    # Modules import the database configuration; isolate even that initialization.
    with tempfile.TemporaryDirectory(prefix='hse_feed_audit_') as directory:
        os.environ['HSE_DATA_DIR'] = directory
        os.environ.pop('GEMINI_API_KEY', None)
        raise SystemExit(asyncio.run(audit()))
