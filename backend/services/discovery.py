import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from ..app.models import Job, EmployerBoard, SearchHistory, SearchPreference, UserProfile
from ..connectors.greenhouse import GreenhouseConnector
from ..connectors.lever import LeverConnector
from ..connectors.base import RawJob
from .matcher import HSEJobMatcher
from .notification_service import check_and_notify_high_match_job

logger = logging.getLogger(__name__)
_matcher = HSEJobMatcher()

# Public ATS boards verified on 2026-11-08. Availability and eligibility can change.
# These are sources, not recommendations or evidence of work authorization.
DEFAULT_BOARDS = [
    {"company_name": "AcuTech Group, Inc.", "platform": "greenhouse", "board_token": "acutechgroupinc", "is_enabled": True},
    {"company_name": "Isar Aerospace SE", "platform": "greenhouse", "board_token": "isaraerospace", "is_enabled": True},
    {"company_name": "Agile Robots SE", "platform": "greenhouse", "board_token": "agilerobotsse", "is_enabled": True},
    {"company_name": "Anduril Industries", "platform": "greenhouse", "board_token": "andurilindustries", "is_enabled": True},
    {"company_name": "EverOn Data Center Services", "platform": "lever", "board_token": "everondcs", "is_enabled": True},
    {"company_name": "Artis BioSolutions", "platform": "lever", "board_token": "landmarkbio", "is_enabled": True},
    {"company_name": "Zero Carbon Systems", "platform": "lever", "board_token": "zerocarbonsystems", "is_enabled": True},
]
LEGACY_BOARDS = {
    ("Canva", "greenhouse", "canva"), ("Stripe", "greenhouse", "stripe"),
    ("Deliveroo", "greenhouse", "deliveroo"), ("GitLab", "greenhouse", "gitlab"),
    ("Gusto", "greenhouse", "gusto"), ("Atlassian", "lever", "atlassian"),
    ("Miro", "lever", "miro"),
}
RETIRED_TOKENS = {"canva", "atlassian", "miro"}
CATALOG_MARKER = "retired: unavailable ATS feed; catalog 2026-11-08"


def init_default_boards(db: Session):
    """Seed fresh installs; upgrade the exact old catalog once without deleting records.

    The retired rows retain a marker so later user enable/delete decisions are
    respected. Custom-only catalogs are never silently expanded or disabled.
    """
    boards = db.query(EmployerBoard).all()
    identities = {(b.company_name, b.platform, b.board_token) for b in boards}
    upgrade = LEGACY_BOARDS.issubset(identities) and not any(
        b.last_status == CATALOG_MARKER for b in boards
    )
    if boards and not upgrade:
        return
    if upgrade:
        for board in boards:
            if (board.company_name, board.platform, board.board_token) in LEGACY_BOARDS and board.board_token in RETIRED_TOKENS:
                board.is_enabled = False
                board.last_status = CATALOG_MARKER
    tokens = {b.board_token for b in boards}
    for entry in DEFAULT_BOARDS:
        if entry["board_token"] not in tokens:
            db.add(EmployerBoard(**entry, created_at=datetime.utcnow()))
    db.commit()

def init_search_preferences(db: Session) -> SearchPreference:
    """Ensure initial search preferences exist."""
    pref = db.query(SearchPreference).first()
    if not pref:
        pref = SearchPreference(
            profile_name="Raghunath Reddy",
            profile_current_role="Global SHE & Security Manager",
            profile_experience_years=18,
            target_countries=json.dumps(["India", "Singapore", "Germany", "Netherlands", "Ireland", "Australia"]),
            target_titles=json.dumps([
                "Global HSE Manager", "Regional HSE Manager", "Corporate HSE Manager",
                "Senior EHS Manager", "Workplace HSE Manager", "Workplace Health & Safety Manager",
                "HSW Manager", "HSE Assurance Manager", "SHE&S Manager", "EHS Lead",
                "HSE Program Manager", "Head of HSE", "HSE Governance Manager",
                "Sustainability & HSE Manager", "Health and Safety Manager", "EHS Manager"
            ]),
            min_match_score=50,
            scoring_weights=json.dumps({
                "experience_seniority": 25,
                "hse_technical_skills": 25,
                "qualifications": 15,
                "industry_relevance": 15,
                "location_international": 15,
                "employment_preferences": 5
            }),
            auto_search_hour=8,
            auto_search_minute=0,
            updated_at=datetime.utcnow()
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref

def is_hse_relevant(title: str, description: str) -> bool:
    """Use the same occupational gate for discovery and scoring.

    The matcher rejects software/sales roles and recognises environmental
    compliance and industrial safety alongside explicit HSE titles.
    """
    return _matcher.classify_occupational_relevance(title, description)[1]


def belongs_to_board(job, board):
    """Reconcile only native URLs with provable ownership; never guess custom links."""
    from urllib.parse import urlsplit, unquote
    if job.source != board.platform.lower() or job.company != board.company_name:
        return False
    parsed = urlsplit(job.url)
    domains = {"greenhouse": {"boards.greenhouse.io", "job-boards.greenhouse.io", "job-boards.eu.greenhouse.io"},
               "lever": {"jobs.lever.co"}}
    if parsed.hostname not in domains.get(board.platform.lower(), set()): return False
    parts = [unquote(p) for p in parsed.path.split("/") if p]
    return bool(parts and parts[0] == board.board_token)


async def run_discovery_service(db: Session, board_id: Optional[int] = None) -> Dict[str, Any]:
    """Refresh complete snapshots transactionally; preserve failed/ambiguous sources."""
    from .matching_context import match_options, apply_score
    init_default_boards(db)
    init_search_preferences(db)
    profile = db.query(UserProfile).first()
    options = match_options(profile, db)
    matcher = HSEJobMatcher()
    query = db.query(EmployerBoard).filter(EmployerBoard.is_enabled.is_(True))
    if board_id: query = query.filter(EmployerBoard.id == board_id)
    boards = query.all()
    history_entry = SearchHistory(started_at=datetime.utcnow(), status="running", boards_searched=len(boards))
    db.add(history_entry); db.commit(); db.refresh(history_entry)
    total_found = total_new = total_updated = total_inactive = successful_boards = 0
    errors = []
    total_fetched = 0
    for board in boards:
        platform = board.platform.lower()
        cls = {"greenhouse": GreenhouseConnector, "lever": LeverConnector}.get(platform)
        if cls is None:
            errors.append(f"{board.company_name}: unsupported platform {platform}")
            continue
        connector = cls(board_token=board.board_token, company_name=board.company_name)
        board.last_searched_at = datetime.utcnow()
        try:
            raw_jobs = await connector.fetch_jobs()
            # Defense in depth for future connectors: invalid snapshots cannot close jobs.
            if not isinstance(raw_jobs, list) or any(not isinstance(j, RawJob) or not j.source_job_id or j.source_job_id == "None" or not j.url for j in raw_jobs):
                raise ValueError("Incomplete or invalid job snapshot.")
            seen = {j.source_job_id for j in raw_jobs}
            seen_urls = {j.url for j in raw_jobs}
            found = new = updated = inactive = 0
            notifications = []
            with db.begin_nested():
                for raw in raw_jobs:
                    existing = db.query(Job).filter(Job.source == raw.source, Job.source_job_id == raw.source_job_id).first()
                    if existing is None:
                        existing = db.query(Job).filter(Job.url == raw.url).first()
                    excluded, _ = matcher.is_excluded(raw.title, raw.description, raw.employment_type)
                    relevant = is_hse_relevant(raw.title, raw.description) and not excluded
                    if existing is None and not relevant: continue
                    result = matcher.evaluate(title=raw.title, location=raw.location, country=raw.country, city=raw.city,
                        employment_type=raw.employment_type, is_permanent_fulltime=raw.is_permanent_fulltime,
                        description=raw.description, **options)
                    if relevant: found += 1
                    if existing is None:
                        existing = Job(source=raw.source, source_job_id=raw.source_job_id, application_status="Discovered", is_saved=False)
                        db.add(existing); new += 1
                    else:
                        updated += 1
                    for field in ("company", "title", "location", "city", "country", "employment_type", "is_permanent_fulltime",
                                  "description", "raw_description_html", "url", "posted_date"):
                        setattr(existing, field, getattr(raw, field))
                    existing.normalized_title = raw.title
                    existing.last_verified_at = datetime.utcnow()
                    existing.is_active = True
                    apply_score(existing, result)
                    if result.score >= 85: notifications.append(existing)
                # Never infer ownership from company name when multiple boards share it.
                count = db.query(EmployerBoard).filter(EmployerBoard.company_name == board.company_name,
                    EmployerBoard.platform == board.platform).count()
                if count == 1:
                    for job in db.query(Job).filter(Job.source == platform, Job.company == board.company_name, Job.is_active.is_(True)).all():
                        if belongs_to_board(job, board) and job.source_job_id not in seen and job.url not in seen_urls:
                            job.is_active = False
                            inactive += 1
                board.last_status = "success"
                board.last_job_count = len(raw_jobs)
            db.commit()
            successful_boards += 1
            total_fetched += len(raw_jobs)
            total_found += found; total_new += new; total_updated += updated; total_inactive += inactive
            # Notifications cannot partially commit the source refresh transaction.
            for job in notifications:
                try: check_and_notify_high_match_job(db, job)
                except Exception as exc:
                    db.rollback(); logger.warning("Notification dispatch failed: %s", exc)
        except Exception as exc:
            db.rollback()
            message = f"{board.company_name} ({platform}): {exc}"
            logger.error(message); errors.append(message)
            board.last_searched_at = datetime.utcnow()
            board.last_status = f"error: {str(exc)[:50]}"
            db.commit()
    history_entry.completed_at = datetime.utcnow()
    history_entry.status = "partial" if successful_boards and errors else ("success" if successful_boards else "failed")
    history_entry.jobs_found = total_found; history_entry.jobs_new = total_new; history_entry.jobs_updated = total_updated
    summary = f"{successful_boards}/{len(boards)} feeds succeeded; {total_fetched} postings fetched; {total_found} HSE vacancies accepted."
    history_entry.error_message = summary + ((" Errors: " + "; ".join(errors)) if errors else "")
    db.commit()
    return dict(status=history_entry.status, boards_searched=len(boards), jobs_found=total_found,
                jobs_new=total_new, jobs_updated=total_updated, jobs_inactivated=total_inactive, errors=errors, boards_succeeded=successful_boards,
                boards_failed=len(boards)-successful_boards, postings_fetched=total_fetched)
