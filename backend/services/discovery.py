import json
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from ..app.models import Job, EmployerBoard, SearchHistory, SearchPreference
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

async def run_discovery_service(db: Session, board_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Execute job discovery run across configured boards.
    Handles duplicate detection, score recalculation, and graceful error recovery.
    """
    init_default_boards(db)
    pref = init_search_preferences(db)
    weights = json.loads(pref.scoring_weights)

    matcher = HSEJobMatcher()

    query = db.query(EmployerBoard).filter(EmployerBoard.is_enabled == True)
    if board_id:
        query = query.filter(EmployerBoard.id == board_id)
    boards = query.all()

    # Record search history entry
    history_entry = SearchHistory(
        started_at=datetime.utcnow(),
        status="running",
        boards_searched=len(boards)
    )
    db.add(history_entry)
    db.commit()
    db.refresh(history_entry)

    total_found = 0
    total_new = 0
    total_updated = 0
    errors: List[str] = []

    for board in boards:
        connector = None
        if board.platform.lower() == "greenhouse":
            connector = GreenhouseConnector(board_token=board.board_token, company_name=board.company_name)
        elif board.platform.lower() == "lever":
            connector = LeverConnector(board_token=board.board_token, company_name=board.company_name)
        else:
            logger.warning(f"Unsupported platform '{board.platform}' for board '{board.company_name}'.")
            continue

        board.last_searched_at = datetime.utcnow()

        try:
            raw_jobs: List[RawJob] = await connector.fetch_jobs()
            board.last_status = "success"
            board.last_job_count = len(raw_jobs)
            
            for raw_job in raw_jobs:
                # 1. Relevance check
                if not is_hse_relevant(raw_job.title, raw_job.description):
                    continue

                # 2. Exclusions (junior safety officers, internships, temp, freelance)
                excluded, reason = matcher.is_excluded(raw_job.title, raw_job.description, raw_job.employment_type)
                if excluded:
                    logger.debug(f"Skipping {raw_job.title} at {raw_job.company}: {reason}")
                    continue

                total_found += 1

                # 3. Evaluate match score
                match_result = matcher.evaluate(
                    title=raw_job.title,
                    location=raw_job.location,
                    country=raw_job.country,
                    city=raw_job.city,
                    employment_type=raw_job.employment_type,
                    is_permanent_fulltime=raw_job.is_permanent_fulltime,
                    description=raw_job.description,
                    weights=weights
                )

                # 4. Deduplication
                existing = db.query(Job).filter(
                    Job.source == raw_job.source,
                    Job.source_job_id == raw_job.source_job_id
                ).first()

                # Fallback URL deduplication if ID differs
                if not existing and raw_job.url:
                    existing = db.query(Job).filter(Job.url == raw_job.url).first()

                if existing:
                    # Update fields while preserving user application status and saved flag
                    existing.last_verified_at = datetime.utcnow()
                    existing.title = raw_job.title
                    existing.location = raw_job.location
                    existing.city = raw_job.city
                    existing.country = raw_job.country
                    existing.employment_type = raw_job.employment_type
                    existing.is_permanent_fulltime = raw_job.is_permanent_fulltime
                    existing.description = raw_job.description
                    existing.match_score = match_result.score
                    existing.match_level = match_result.level
                    existing.match_reasons = json.dumps(match_result.reasons)
                    existing.matching_qualifications = json.dumps(match_result.matching_qualifications)
                    existing.matching_experience = json.dumps(match_result.matching_experience)
                    existing.matching_skills = json.dumps(match_result.matching_skills)
                    existing.missing_requirements = json.dumps(match_result.missing_requirements)
                    existing.location_suitability = match_result.location_suitability
                    existing.sponsorship_status = match_result.sponsorship_status
                    existing.is_active = True
                    total_updated += 1
                else:
                    new_job = Job(
                        source=raw_job.source,
                        source_job_id=raw_job.source_job_id,
                        company=raw_job.company,
                        title=raw_job.title,
                        normalized_title=raw_job.title,
                        location=raw_job.location,
                        city=raw_job.city,
                        country=raw_job.country,
                        employment_type=raw_job.employment_type,
                        is_permanent_fulltime=raw_job.is_permanent_fulltime,
                        description=raw_job.description,
                        raw_description_html=raw_job.raw_description_html,
                        url=raw_job.url,
                        posted_date=raw_job.posted_date,
                        discovered_at=datetime.utcnow(),
                        last_verified_at=datetime.utcnow(),
                        is_active=True,
                        match_score=match_result.score,
                        match_level=match_result.level,
                        match_reasons=json.dumps(match_result.reasons),
                        matching_qualifications=json.dumps(match_result.matching_qualifications),
                        matching_experience=json.dumps(match_result.matching_experience),
                        matching_skills=json.dumps(match_result.matching_skills),
                        missing_requirements=json.dumps(match_result.missing_requirements),
                        location_suitability=match_result.location_suitability,
                        sponsorship_status=match_result.sponsorship_status,
                        application_status="Discovered",
                        is_saved=False
                    )
                    db.add(new_job)
                    total_new += 1
                    if match_result.score >= 85:
                        try:
                            check_and_notify_high_match_job(db, new_job)
                        except Exception as n_err:
                            logger.warning(f"Notification error: {n_err}")

            db.commit()

        except Exception as exc:
            err_msg = f"{board.company_name} ({board.platform}): {str(exc)}"
            logger.error(f"Error discovering jobs for {err_msg}")
            board.last_status = f"error: {str(exc)[:50]}"
            errors.append(err_msg)
            db.commit()

    # Update history run
    history_entry.completed_at = datetime.utcnow()
    history_entry.status = "success" if not errors or total_found > 0 else "failed"
    history_entry.jobs_found = total_found
    history_entry.jobs_new = total_new
    history_entry.jobs_updated = total_updated
    if errors:
        history_entry.error_message = "; ".join(errors)
    db.commit()

    return {
        "status": history_entry.status,
        "boards_searched": len(boards),
        "jobs_found": total_found,
        "jobs_new": total_new,
        "jobs_updated": total_updated,
        "errors": errors
    }
