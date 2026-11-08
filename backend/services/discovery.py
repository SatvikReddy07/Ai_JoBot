import json
import logging
import re
from datetime import datetime, timezone
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

# Default reputable multinational employer boards using Greenhouse and Lever
DEFAULT_BOARDS = [
    {"company_name": "Canva", "platform": "greenhouse", "board_token": "canva", "is_enabled": True},
    {"company_name": "Stripe", "platform": "greenhouse", "board_token": "stripe", "is_enabled": True},
    {"company_name": "Deliveroo", "platform": "greenhouse", "board_token": "deliveroo", "is_enabled": True},
    {"company_name": "GitLab", "platform": "greenhouse", "board_token": "gitlab", "is_enabled": True},
    {"company_name": "Gusto", "platform": "greenhouse", "board_token": "gusto", "is_enabled": True},
    {"company_name": "Atlassian", "platform": "lever", "board_token": "atlassian", "is_enabled": True},
    {"company_name": "Miro", "platform": "lever", "board_token": "miro", "is_enabled": True},
]

def init_default_boards(db: Session):
    """Seed default employer boards if empty."""
    existing_count = db.query(EmployerBoard).count()
    if existing_count == 0:
        for b in DEFAULT_BOARDS:
            board = EmployerBoard(
                company_name=b["company_name"],
                platform=b["platform"],
                board_token=b["board_token"],
                is_enabled=b["is_enabled"],
                created_at=datetime.utcnow()
            )
            db.add(board)
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
    """
    Check if role is relevant to HSE, Workplace Safety, Environment, or ESG leadership.
    Uses regex word boundaries and rejects non-HSE titles to prevent false positive discovery.
    """
    title_lower = title.lower()
    desc_sample = description[:1200].lower()

    # Reject non-HSE domain titles (e.g., Software Engineering Manager, Sales Lead) unless explicitly HSE
    is_core_hse_title = any(re.search(pat, title_lower) for pat in _matcher.HSE_CORE_TITLE_PATTERNS)
    is_non_hse = any(re.search(pat, title_lower) for pat in _matcher.NON_HSE_DOMAINS)
    if is_non_hse and not is_core_hse_title:
        return False

    # Title check first
    if is_core_hse_title:
        return True

    # Description check using word-boundary regex patterns
    hse_desc_patterns = [
        r"\bhse\b", r"\behs\b", r"\bshe&s\b", r"\bshe\s+(manager|director|lead|governance)\b",
        r"\bhsw\b", r"\bqhse\b",
        r"\bhealth\s*(and|&)\s*safety\b", r"\bworkplace\s*health\b", r"\bworkplace\s*safety\b",
        r"\boccupational\s*(health|safety)\b", r"\benvironment(al)?\s*health\b",
        r"\bsafety\s*(manager|lead|director|governance|assurance|framework|culture)\b",
        r"\bhead\s*of\s*safety\b", r"\bincident\s*investigation\b", r"\bprocess\s*safety\b",
        r"\biso\s*45001\b", r"\biso\s*14001\b", r"\bhazop\b", r"\bltif\b", r"\btrir\b"
    ]

    return any(re.search(p, desc_sample) for p in hse_desc_patterns)

def belongs_to_board(job, board):
    """Reconcile only native URLs with provable ownership; never guess custom links."""
    from urllib.parse import urlsplit, unquote
    if job.source != board.platform.lower() or job.company != board.company_name:
        return False
    parsed = urlsplit(job.url)
    domains = {"greenhouse": {"boards.greenhouse.io", "job-boards.greenhouse.io"},
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
    history_entry.status = "success" if successful_boards else "failed"
    history_entry.jobs_found = total_found; history_entry.jobs_new = total_new; history_entry.jobs_updated = total_updated
    history_entry.error_message = "; ".join(errors) or None
    db.commit()
    return dict(status=history_entry.status, boards_searched=len(boards), jobs_found=total_found,
                jobs_new=total_new, jobs_updated=total_updated, jobs_inactivated=total_inactive, errors=errors)
