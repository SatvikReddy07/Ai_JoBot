import os
import json
import shutil
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from fastapi import FastAPI, Depends, HTTPException, Query, Response, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc

from .database import engine, get_db, Base, DATA_DIR, initialize_schema
from .models import (
    Job, EmployerBoard, SearchPreference, SearchHistory, ApplicationHistory,
    MasterCV, UserProfile, AIJobAssessment, AIUsageLog,
    ApplicationPackage, GeneratedDocument, DocumentVersion, DocumentApproval,
    GenerationAuditLog, DesktopNotificationLog
)
from .schemas import (
    JobResponse, JobListResponse, JobStatusUpdate, JobSaveToggle,
    EmployerBoardResponse, EmployerBoardCreate, EmployerBoardUpdate,
    SettingsResponse, SettingsUpdate, ScoringWeights,
    SearchRunResponse, SearchHistoryResponse, DashboardStatsResponse,
    MasterCVResponse, UserProfileResponse, UserProfileUpdate, UserConsentToggle,
    AIJobAssessmentResponse, AIUsageStatsResponse, CVUploadResponse,
    TailoredCVContent, TailoredCoverLetterContent, ATSKeywordAnalysisResponse,
    GeneratedDocumentResponse, DocumentApprovalResponse, ApplicationPackageResponse,
    PackageGenerateRequest, DocumentUpdateRequest, PackageApproveRequest, NotificationConfig
)

from ..services.discovery import run_discovery_service, init_default_boards, init_search_preferences
from ..services.export import generate_jobs_csv
from ..services.cv_parser import extract_text_from_file, parse_cv_content
from ..services.gemini_service import (
    analyze_job_with_ai, get_daily_ai_usage, DEFAULT_GEMINI_MODEL, DEFAULT_DAILY_LIMIT, cached_assessment_is_current
)
from ..services.ats_service import analyze_ats_keywords
from ..services.tailoring_service import generate_tailored_cv, generate_tailored_cover_letter
from ..services.package_service import (
    create_application_package, update_document_content, approve_package,
    format_package_response, PACKAGES_DIR
)
from ..services.notification_service import check_and_notify_high_match_job, send_desktop_notification
from ..services.cv_generator import check_pdf_converter_availability

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hse_agent")

# Ensure CV storage directory exists
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CV_DIR = DATA_DIR / "cv"
CV_DIR.mkdir(parents=True, exist_ok=True)

# Initialize database schema
initialize_schema()

app = FastAPI(
    title="HSE Career Agent API",
    description="Backend API for personal HSE leadership career discovery, AI matching, and tracking",
    version="4.1.0"
)

# Reject DNS rebinding and unsafe cross-origin requests, including same-site port attacks.
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"])

@app.middleware("http")
async def local_origin_guard(request, call_next):
    origin = request.headers.get("origin")
    if origin and origin not in {"http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"}:
        return JSONResponse({"detail": "Untrusted browser origin."}, status_code=403)
    return await call_next(request)

# Localhost security and CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_or_create_user_profile(db: Session) -> UserProfile:
    """Ensure UserProfile baseline for Raghunath Reddy is always populated."""
    profile = db.query(UserProfile).first()
    if not profile:
        profile = UserProfile(
            name="Raghunath Reddy",
            current_role="Global SHE & Security Manager",
            current_company="dsm-firmenich",
            location="Hyderabad, India",
            experience_years=18,
            summary=(
                "Accomplished Global SHE & Security executive with 18+ years of multinational leadership "
                "experience overseeing environmental engineering, workplace safety, and corporate governance "
                "across APAC and global operations. Currently managing APAC HSE reporting across 19 plants."
            ),
            employment_history=json.dumps([
                {"company": "dsm-firmenich", "role": "Global SHE & Security Manager", "location": "Hyderabad", "highlights": ["APAC reporting across 19 plants", "Overseeing corporate workplace HSE and governance"], "source": "verified_profile"},
                {"company": "Wavin-Orbia", "role": "Regional HSE Lead", "location": "India", "highlights": ["Multi-site workplace safety leadership", "Contractor safety management"], "source": "verified_profile"},
                {"company": "Toshiba/TLI", "role": "EHS Manager", "location": "India", "highlights": ["ISO 14001 and ISO 45001 implementation", "Statutory compliance and audits"], "source": "verified_profile"},
                {"company": "Larsen & Toubro", "role": "Assistant Manager — Maintenance and Operations (through November 2016)", "location": "India", "highlights": ["Preventive and breakdown maintenance; plant operations", "Equipment reliability, installation, commissioning and projects", "Team, contractor, manpower, maintenance budget and procurement management"], "source": "verified_profile"},
                {"company": "Dharti Dredging", "role": "Safety Officer / In-Charge", "location": "India", "highlights": ["Industrial safety and marine operations risk management"], "source": "verified_profile"}
            ]),
            qualifications=json.dumps([
                "M.Tech Environmental Engineering (Completed, degree awarded)",
                "B.Tech Mechanical Engineering",
                "MBA Human Resources",
                "Diploma in Industrial Safety"
            ]),
            skills=json.dumps([
                "Corporate and Global HSE Management",
                "Regional and APAC HSE Leadership",
                "Workplace Health and Safety Governance",
                "ISO 14001 & ISO 45001 Management Systems",
                "Contractor Safety Management",
                "Incident Investigation & Root Cause Analysis (RCA)",
                "HSE Audits and Statutory Compliance",
                "Sustainability and ESG Reporting",
                "Risk Assessment & Management (HAZOP / HIRA / JHA)",
                "Employee Health, Wellness & Safety Culture",
                "HSE Performance Reporting & Analytics"
            ]),
            certifications=json.dumps([
                "Diploma in Industrial Safety",
                "ISO 14001 Environmental Management Systems",
                "ISO 45001 Occupational Health & Safety Systems"
            ]),
            achievements=json.dumps([
                "Directed APAC HSE performance reporting and compliance governance across 19 manufacturing plants.",
                "Over 18+ years of leadership in corporate SHE and security for global multinationals."
            ]),
            target_countries=json.dumps(["India", "Singapore", "Germany", "Netherlands", "Ireland", "Australia"]),
            target_titles=json.dumps([
                "Global HSE Manager", "Regional HSE Manager", "Corporate HSE Manager",
                "Senior EHS Manager", "Workplace HSE Manager", "Workplace Health & Safety Manager",
                "HSW Manager", "HSE Assurance Manager", "SHE&S Manager", "Head of HSE",
                "HSE Governance Manager", "Sustainability & HSE Manager", "EHS Lead"
            ]),
            consent_given_for_ai=False,
            last_updated_at=datetime.utcnow()
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile

def format_user_profile_response(profile: UserProfile) -> dict:
    """Format UserProfile into typed response dictionary."""
    cv_data = None
    if profile.cv:
        cv_data = {
            "id": profile.cv.id,
            "filename": profile.cv.filename,
            "file_type": profile.cv.file_type,
            "file_size": profile.cv.file_size,
            "extracted_at": profile.cv.extracted_at,
            "is_active": profile.cv.is_active
        }

    return {
        "id": profile.id,
        "name": profile.name,
        "current_role": profile.current_role,
        "current_company": profile.current_company,
        "location": profile.location,
        "experience_years": profile.experience_years,
        "summary": profile.summary,
        "employment_history": json.loads(profile.employment_history or "[]"),
        "qualifications": json.loads(profile.qualifications or "[]"),
        "skills": json.loads(profile.skills or "[]"),
        "certifications": json.loads(profile.certifications or "[]"),
        "achievements": json.loads(profile.achievements or "[]"),
        "target_countries": json.loads(profile.target_countries or "[]"),
        "target_titles": json.loads(profile.target_titles or "[]"),
        "consent_given_for_ai": profile.consent_given_for_ai,
        "last_updated_at": profile.last_updated_at,
        "cv": cv_data
    }

def format_job_response(j: Job) -> dict:
    """Format SQLAlchemy Job model into dict matching JobResponse."""
    ai_data = None
    from sqlalchemy.orm import object_session
    db = object_session(j)
    if j.ai_assessment and db is not None and cached_assessment_is_current(db, j):
        ai_data = {
            "id": j.ai_assessment.id,
            "job_id": j.ai_assessment.job_id,
            "job_hash": j.ai_assessment.job_hash,
            "match_score": j.ai_assessment.match_score,
            "application_priority": j.ai_assessment.application_priority,
            "career_growth_score": j.ai_assessment.career_growth_score,
            "career_growth_summary": j.ai_assessment.career_growth_summary,
            "matching_skills": json.loads(j.ai_assessment.matching_skills or "[]"),
            "missing_requirements": json.loads(j.ai_assessment.missing_requirements or "[]"),
            "qualification_alignment": json.loads(j.ai_assessment.qualification_alignment or "[]"),
            "experience_alignment": json.loads(j.ai_assessment.experience_alignment or "[]"),
            "industry_alignment": json.loads(j.ai_assessment.industry_alignment or "[]"),
            "visa_relocation_considerations": j.ai_assessment.visa_relocation_considerations,
            "reasons_to_apply": json.loads(j.ai_assessment.reasons_to_apply or "[]"),
            "reasons_to_reconsider": json.loads(j.ai_assessment.reasons_to_reconsider or "[]"),
            "evidence_references": json.loads(j.ai_assessment.evidence_references or "{}"),
            "model_used": j.ai_assessment.model_used,
            "engine_used": j.ai_assessment.engine_used,
            "created_at": j.ai_assessment.created_at
        }

    return {
        "id": j.id,
        "source": j.source,
        "source_job_id": j.source_job_id,
        "company": j.company,
        "title": j.title,
        "normalized_title": j.normalized_title,
        "location": j.location,
        "city": j.city,
        "country": j.country,
        "employment_type": j.employment_type,
        "is_permanent_fulltime": j.is_permanent_fulltime,
        "description": j.description,
        "raw_description_html": j.raw_description_html,
        "url": j.url,
        "posted_date": j.posted_date,
        "discovered_at": j.discovered_at,
        "last_verified_at": j.last_verified_at,
        "is_active": j.is_active,
        "match_score": j.match_score,
        "match_level": j.match_level,
        "match_reasons": json.loads(j.match_reasons or "[]"),
        "matching_qualifications": json.loads(j.matching_qualifications or "[]"),
        "matching_experience": json.loads(j.matching_experience or "[]"),
        "matching_skills": json.loads(j.matching_skills or "[]"),
        "missing_requirements": json.loads(j.missing_requirements or "[]"),
        "location_suitability": j.location_suitability,
        "sponsorship_status": j.sponsorship_status,
        "application_status": j.application_status,
        "application_notes": j.application_notes,
        "is_saved": j.is_saved,
        "ai_assessment": ai_data,
        "managed_application": bool(j.applications)
    }

@app.on_event("startup")
def startup_event():
    with next(get_db()) as db:
        init_default_boards(db)
        init_search_preferences(db)
        get_or_create_user_profile(db)
        from ..services.matching_context import refresh_job_scores
        refresh_job_scores(db)
        db.commit()

# 1. Health
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": "HSE Career Agent",
        "version": "4.1.0",
        "phase": 4,
        "timestamp": datetime.utcnow().isoformat()
    }

# 2. Dashboard Statistics
@app.get("/api/dashboard/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(db: Session = Depends(get_db)):
    today_start = datetime.combine(date.today(), datetime.min.time())

    total_jobs = db.query(Job).count()
    new_jobs_today = db.query(Job).filter(Job.discovered_at >= today_start).count()
    excellent_matches = db.query(Job).filter(Job.is_active.is_(True), Job.match_score >= 85).count()
    strong_matches = db.query(Job).filter(Job.is_active.is_(True), Job.match_score >= 75, Job.match_score < 85).count()
    saved_opportunities = db.query(Job).filter(Job.is_saved == True).count()
    active_applications = db.query(Job).filter(
        Job.application_status.in_(["Interested", "Ready to Apply", "Applied", "Interview", "Offer", "Shortlisted", "Documents Prepared", "Ready For Review", "In Progress", "Submitted", "Follow Up Due", "Interview Scheduled", "Offer Received"])
    ).count()

    ai_analyzed_count = db.query(AIJobAssessment).count()

    last_search = db.query(SearchHistory).filter(
        SearchHistory.status == "success"
    ).order_by(desc(SearchHistory.completed_at)).first()

    last_search_time = last_search.completed_at if last_search else None

    return {
        "total_jobs": total_jobs,
        "new_jobs_today": new_jobs_today,
        "excellent_matches": excellent_matches,
        "strong_matches": strong_matches,
        "saved_opportunities": saved_opportunities,
        "active_applications": active_applications,
        "last_successful_search": last_search_time,
        "ai_analyzed_count": ai_analyzed_count
    }

# 3. CSV Export
@app.get("/api/jobs/export")
def export_jobs_csv(
    country: Optional[str] = None,
    min_score: Optional[int] = None,
    application_status: Optional[str] = None,
    is_saved: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Job)
    if country and country != "All":
        query = query.filter(Job.country == country)
    if min_score is not None:
        query = query.filter(Job.match_score >= min_score)
    if application_status and application_status != "All":
        query = query.filter(Job.application_status == application_status)
    if is_saved is not None:
        query = query.filter(Job.is_saved == is_saved)

    jobs = query.order_by(desc(Job.match_score)).all()
    csv_file = generate_jobs_csv(jobs)

    filename = f"hse_opportunities_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_file.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# 4. Job Search & Filtering
@app.get("/api/jobs", response_model=JobListResponse)
def get_jobs(
    q: Optional[str] = None,
    country: Optional[str] = None,
    city: Optional[str] = None,
    company: Optional[str] = None,
    job_title: Optional[str] = None,
    min_score: Optional[int] = None,
    match_level: Optional[str] = None,
    employment_type: Optional[str] = None,
    sponsorship_status: Optional[str] = None,
    application_status: Optional[str] = None,
    is_saved: Optional[bool] = None,
    ai_priority: Optional[str] = None,
    sort_by: str = "score_desc",
    include_inactive: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Job)
    if not include_inactive:
        query = query.filter(Job.is_active.is_(True))

    if q:
        search_filter = f"%{q}%"
        query = query.filter(
            (Job.title.ilike(search_filter)) |
            (Job.company.ilike(search_filter)) |
            (Job.location.ilike(search_filter)) |
            (Job.description.ilike(search_filter))
        )

    if country and country != "All":
        query = query.filter(Job.country == country)

    if city:
        query = query.filter(Job.city.ilike(f"%{city}%"))

    if company:
        query = query.filter(Job.company.ilike(f"%{company}%"))

    if job_title:
        query = query.filter(Job.title.ilike(f"%{job_title}%"))

    if min_score is not None:
        query = query.filter(Job.match_score >= min_score)

    if match_level and match_level != "All":
        query = query.filter(Job.match_level == match_level)

    if employment_type and employment_type != "All":
        query = query.filter(Job.employment_type == employment_type)

    if sponsorship_status and sponsorship_status != "All":
        query = query.filter(Job.sponsorship_status == sponsorship_status)

    if application_status and application_status != "All":
        query = query.filter(Job.application_status == application_status)

    if is_saved is not None:
        query = query.filter(Job.is_saved == is_saved)

    if ai_priority and ai_priority != "All":
        query = query.join(AIJobAssessment, Job.id == AIJobAssessment.job_id).filter(
            AIJobAssessment.application_priority == ai_priority
        )

    # Sorting
    if sort_by == "score_desc":
        query = query.order_by(desc(Job.match_score), desc(Job.discovered_at))
    elif sort_by == "score_asc":
        query = query.order_by(asc(Job.match_score))
    elif sort_by == "date_desc":
        query = query.order_by(desc(Job.discovered_at))
    elif sort_by == "company_asc":
        query = query.order_by(asc(Job.company))
    else:
        query = query.order_by(desc(Job.match_score))

    query = query.order_by(Job.id.asc())
    total = query.count()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    jobs = query.offset((page - 1) * page_size).limit(page_size).all()
    formatted = [format_job_response(j) for j in jobs]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "items": formatted
    }

# 5. Job Details
@app.get("/api/jobs/{job_id}", response_model=JobResponse)
def get_job_by_id(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job vacancy not found")
    return format_job_response(job)

# 6. Save/Unsave Job
@app.post("/api/jobs/{job_id}/save")
def toggle_save_job(job_id: int, payload: JobSaveToggle, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job vacancy not found")

    job.is_saved = payload.is_saved
    if payload.is_saved and job.application_status == "Discovered":
        job.application_status = "Saved"
    elif not payload.is_saved and job.application_status == "Saved":
        job.application_status = "Discovered"

    db.commit()
    return {"message": "Job save status updated", "is_saved": job.is_saved, "application_status": job.application_status}

# 7. Update Application Status
@app.put("/api/jobs/{job_id}/status")
def update_job_status(job_id: int, payload: JobStatusUpdate, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job vacancy not found")

    valid_statuses = [
        "Discovered", "Saved", "Interested", "Ready to Apply",
        "Applied", "Interview", "Offer", "Rejected", "Closed"
    ]
    if payload.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

    from .models import JobApplication
    if db.query(JobApplication).filter_by(job_id=job_id).first():
        raise HTTPException(status_code=409, detail="Use Application Control Center for this application's stage and confirmation.")
    previous_status = job.application_status
    job.application_status = payload.status
    if payload.notes is not None:
        job.application_notes = payload.notes

    if payload.status in ["Saved", "Interested", "Ready to Apply", "Applied", "Interview", "Offer"]:
        job.is_saved = True

    history = ApplicationHistory(
        job_id=job.id,
        previous_status=previous_status,
        new_status=payload.status,
        notes=payload.notes,
        changed_at=datetime.utcnow()
    )
    db.add(history)
    db.commit()

    return {
        "message": "Application status updated successfully",
        "job_id": job.id,
        "previous_status": previous_status,
        "current_status": job.application_status
    }

# 8. Run Search Now
@app.post("/api/search/run", response_model=SearchRunResponse)
async def trigger_search(board_id: Optional[int] = None, db: Session = Depends(get_db)):
    result = await run_discovery_service(db, board_id=board_id)
    return {
        "status": result["status"],
        "boards_succeeded": result["boards_succeeded"],
        "boards_failed": result["boards_failed"],
        "postings_fetched": result["postings_fetched"],
        "errors": result["errors"],
        "boards_searched": result["boards_searched"],
        "jobs_found": result["jobs_found"],
        "jobs_new": result["jobs_new"],
        "jobs_updated": result["jobs_updated"],
        "message": f"Discovery {result['status']}: {result['boards_succeeded']}/{result['boards_searched']} feeds succeeded, {result['boards_failed']} failed; {result['postings_fetched']} postings fetched, {result['jobs_found']} HSE vacancies accepted; {result['jobs_new']} new, {result['jobs_updated']} updated. See Search History for diagnostics."
    }

# 9. Search History
@app.get("/api/search/history", response_model=List[SearchHistoryResponse])
def get_search_history(db: Session = Depends(get_db)):
    history = db.query(SearchHistory).order_by(desc(SearchHistory.started_at)).limit(50).all()
    return history

# 10. Settings
@app.get("/api/settings", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    pref = init_search_preferences(db)
    weights_dict = json.loads(pref.scoring_weights)

    return {
        "profile_name": pref.profile_name,
        "profile_current_role": pref.profile_current_role,
        "profile_experience_years": pref.profile_experience_years,
        "target_countries": json.loads(pref.target_countries),
        "target_titles": json.loads(pref.target_titles),
        "min_match_score": pref.min_match_score,
        "scoring_weights": ScoringWeights(**weights_dict),
        "auto_search_hour": pref.auto_search_hour,
        "auto_search_minute": pref.auto_search_minute,
        "updated_at": pref.updated_at,
        "gemini_model": os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
        "ai_daily_limit": int(os.getenv("AI_DAILY_LIMIT", str(DEFAULT_DAILY_LIMIT))),
        "api_key_configured": bool(os.getenv("GEMINI_API_KEY", "").strip())
    }

@app.put("/api/settings", response_model=SettingsResponse)
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    pref = init_search_preferences(db)

    if payload.profile_name is not None:
        pref.profile_name = payload.profile_name
    if payload.profile_current_role is not None:
        pref.profile_current_role = payload.profile_current_role
    if payload.profile_experience_years is not None:
        pref.profile_experience_years = payload.profile_experience_years
    if payload.target_countries is not None:
        pref.target_countries = json.dumps(payload.target_countries)
    if payload.target_titles is not None:
        pref.target_titles = json.dumps(payload.target_titles)
    if payload.min_match_score is not None:
        pref.min_match_score = payload.min_match_score
    if payload.scoring_weights is not None:
        pref.scoring_weights = json.dumps(payload.scoring_weights.dict())
    if payload.auto_search_hour is not None:
        pref.auto_search_hour = payload.auto_search_hour
    if payload.auto_search_minute is not None:
        pref.auto_search_minute = payload.auto_search_minute
    if payload.gemini_model is not None:
        os.environ["GEMINI_MODEL"] = payload.gemini_model
    if payload.ai_daily_limit is not None:
        os.environ["AI_DAILY_LIMIT"] = str(payload.ai_daily_limit)

    pref.updated_at = datetime.utcnow()
    if payload.scoring_weights is not None or payload.target_countries is not None:
        from ..services.matching_context import refresh_job_scores
        refresh_job_scores(db)
    db.commit()
    db.refresh(pref)

    weights_dict = json.loads(pref.scoring_weights)
    return {
        "profile_name": pref.profile_name,
        "profile_current_role": pref.profile_current_role,
        "profile_experience_years": pref.profile_experience_years,
        "target_countries": json.loads(pref.target_countries),
        "target_titles": json.loads(pref.target_titles),
        "min_match_score": pref.min_match_score,
        "scoring_weights": ScoringWeights(**weights_dict),
        "auto_search_hour": pref.auto_search_hour,
        "auto_search_minute": pref.auto_search_minute,
        "updated_at": pref.updated_at,
        "gemini_model": os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
        "ai_daily_limit": int(os.getenv("AI_DAILY_LIMIT", str(DEFAULT_DAILY_LIMIT))),
        "api_key_configured": bool(os.getenv("GEMINI_API_KEY", "").strip())
    }

# 11. Employer Boards Management
@app.get("/api/employers", response_model=List[EmployerBoardResponse])
def get_employer_boards(db: Session = Depends(get_db)):
    init_default_boards(db)
    boards = db.query(EmployerBoard).order_by(asc(EmployerBoard.company_name)).all()
    return boards

@app.post("/api/employers", response_model=EmployerBoardResponse)
def add_employer_board(payload: EmployerBoardCreate, db: Session = Depends(get_db)):
    platform = payload.platform.lower().strip()
    if platform not in ["greenhouse", "lever"]:
        raise HTTPException(status_code=400, detail="Platform must be either 'greenhouse' or 'lever'")

    token = payload.board_token.strip().lower()
    existing = db.query(EmployerBoard).filter(EmployerBoard.board_token == token).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Employer board with token '{token}' already exists.")

    board = EmployerBoard(
        company_name=payload.company_name.strip(),
        platform=platform,
        board_token=token,
        is_enabled=payload.is_enabled,
        created_at=datetime.utcnow()
    )
    db.add(board)
    db.commit()
    db.refresh(board)
    return board

@app.put("/api/employers/{board_id}", response_model=EmployerBoardResponse)
def update_employer_board(board_id: int, payload: EmployerBoardUpdate, db: Session = Depends(get_db)):
    board = db.query(EmployerBoard).filter(EmployerBoard.id == board_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Employer board not found")

    if payload.company_name is not None:
        board.company_name = payload.company_name.strip()
    if payload.platform is not None:
        p = payload.platform.lower().strip()
        if p not in ["greenhouse", "lever"]:
            raise HTTPException(status_code=400, detail="Platform must be 'greenhouse' or 'lever'")
        board.platform = p
    if payload.board_token is not None:
        token = payload.board_token.strip().lower()
        dup = db.query(EmployerBoard).filter(
            EmployerBoard.board_token == token,
            EmployerBoard.id != board_id
        ).first()
        if dup:
            raise HTTPException(status_code=400, detail=f"Board token '{token}' is already used by another board.")
        board.board_token = token
    if payload.is_enabled is not None:
        board.is_enabled = payload.is_enabled

    db.commit()
    db.refresh(board)
    return board

@app.delete("/api/employers/{board_id}")
def delete_employer_board(board_id: int, db: Session = Depends(get_db)):
    board = db.query(EmployerBoard).filter(EmployerBoard.id == board_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Employer board not found")
    db.delete(board)
    db.commit()
    return {"message": f"Employer board '{board.company_name}' deleted successfully."}

# ==================== PHASE 2 ENDPOINTS ====================

# 12. CV Upload and Text Extraction
@app.post("/api/profile/upload-cv", response_model=CVUploadResponse)
async def upload_master_cv(file: UploadFile = File(...), db: Session = Depends(get_db)):

    filename = Path((file.filename or "cv_upload").replace("\\", "/")).name
    ext = Path(filename).suffix.lower()

    if ext not in [".pdf", ".docx"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{ext}'. Only .pdf and .docx files are permitted."
        )

    # Save file securely to local data/cv directory
    timestamp_prefix = __import__("uuid").uuid4().hex
    safe_filename = f"{timestamp_prefix}{ext}"
    target_path = CV_DIR / safe_filename

    try:
        with open(target_path, "wb") as buffer:
            total = 0
            while chunk := file.file.read(1024 * 1024):
                total += len(chunk)
                if total > 10 * 1024 * 1024:
                    raise HTTPException(status_code=413, detail="CV must be at most 10 MiB.")
                buffer.write(chunk)
        file_size = target_path.stat().st_size
        if file_size == 0:
            target_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")
    except HTTPException:
        target_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        target_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Failed to save uploaded CV.")

    # Extract text using PyMuPDF or python-docx
    try:
        raw_text = extract_text_from_file(target_path, filename)
    except Exception as exc:
        target_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc))

    if not raw_text.strip():
        target_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Uploaded CV yielded empty text. Please check the document.")

    # Mark previous CVs as inactive
    db.query(MasterCV).update({MasterCV.is_active: False})

    # Record new MasterCV
    master_cv = MasterCV(
        filename=filename,
        file_type=ext.replace(".", ""),
        stored_path=str(target_path),
        raw_text=raw_text,
        file_size=file_size,
        extracted_at=datetime.utcnow(),
        is_active=True
    )
    db.add(master_cv)
    db.commit()
    db.refresh(master_cv)

    # Parse and update UserProfile
    profile = get_or_create_user_profile(db)
    parsed = parse_cv_content(raw_text, existing_profile=format_user_profile_response(profile))

    profile.name = parsed["name"]
    profile.current_role = parsed["current_role"]
    profile.current_company = parsed["current_company"]
    profile.location = parsed["location"]
    profile.experience_years = parsed["experience_years"]
    profile.summary = parsed["summary"]
    profile.employment_history = json.dumps(parsed["employment_history"])
    profile.qualifications = json.dumps(parsed["qualifications"])
    profile.skills = json.dumps(parsed["skills"])
    profile.certifications = json.dumps(parsed["certifications"])
    profile.achievements = json.dumps(parsed["achievements"])
    profile.target_countries = json.dumps(parsed["target_countries"])
    profile.target_titles = json.dumps(parsed["target_titles"])
    profile.cv_id = master_cv.id
    profile.last_updated_at = datetime.utcnow()

    db.commit()
    db.refresh(profile)

    return {
        "message": f"CV '{filename}' uploaded. Confirmed profile preserved; review the CV and edit profile fields explicitly.",
        "cv_id": master_cv.id,
        "filename": filename,
        "profile": format_user_profile_response(profile)
    }

# 13. Get Candidate Profile

@app.get("/api/profile", response_model=UserProfileResponse)
def get_user_profile(db: Session = Depends(get_db)):
    profile = get_or_create_user_profile(db)
    return format_user_profile_response(profile)

# 14. Update/Confirm Profile Fields
@app.put("/api/profile", response_model=UserProfileResponse)
def update_user_profile(payload: UserProfileUpdate, db: Session = Depends(get_db)):
    profile = get_or_create_user_profile(db)

    if payload.name is not None:
        profile.name = payload.name
    if payload.current_role is not None:
        profile.current_role = payload.current_role
    if payload.current_company is not None:
        profile.current_company = payload.current_company
    if payload.location is not None:
        profile.location = payload.location
    if payload.experience_years is not None:
        profile.experience_years = payload.experience_years
    if payload.summary is not None:
        profile.summary = payload.summary
    if payload.employment_history is not None:
        profile.employment_history = json.dumps([h.dict() for h in payload.employment_history])
    if payload.qualifications is not None:
        profile.qualifications = json.dumps(payload.qualifications)
    if payload.skills is not None:
        profile.skills = json.dumps(payload.skills)
    if payload.certifications is not None:
        profile.certifications = json.dumps(payload.certifications)
    if payload.achievements is not None:
        profile.achievements = json.dumps(payload.achievements)
    if payload.target_countries is not None:
        profile.target_countries = json.dumps(payload.target_countries)
        init_search_preferences(db).target_countries = profile.target_countries
    if payload.target_titles is not None:
        profile.target_titles = json.dumps(payload.target_titles)
    if payload.consent_given_for_ai is not None:
        profile.consent_given_for_ai = payload.consent_given_for_ai

    profile.last_updated_at = datetime.utcnow()
    from ..services.matching_context import refresh_job_scores
    refresh_job_scores(db)
    db.commit()
    db.refresh(profile)

    return format_user_profile_response(profile)

# 15. Toggle AI Privacy Consent
@app.post("/api/profile/consent")
def set_ai_consent(payload: UserConsentToggle, db: Session = Depends(get_db)):
    profile = get_or_create_user_profile(db)
    profile.consent_given_for_ai = payload.consent_given
    profile.last_updated_at = datetime.utcnow()
    db.commit()
    return {
        "message": "AI privacy consent updated successfully",
        "consent_given_for_ai": profile.consent_given_for_ai
    }

# 16. Download Master CV File
@app.get("/api/profile/cv/download")
def download_master_cv(db: Session = Depends(get_db)):
    cv = db.query(MasterCV).filter(MasterCV.is_active == True).order_by(desc(MasterCV.extracted_at)).first()
    if not cv:
        raise HTTPException(status_code=404, detail="No active master CV file found.")
    path = Path(cv.stored_path).resolve()
    if not path.exists():
        # Resolve legacy Windows paths locally without changing the stored record.
        path = (CV_DIR / Path(cv.stored_path.replace("\\", "/")).name).resolve()
    if not path.is_relative_to(CV_DIR.resolve()):
        raise HTTPException(status_code=403, detail="CV path is outside local CV storage.")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Master CV file unavailable in local storage.")
    return FileResponse(
        path=str(path),
        filename=cv.filename,
        media_type="application/octet-stream"
    )

# 17. AI Analyze Job (with Caching & Rate Limiting)
@app.post("/api/jobs/{job_id}/ai-analyze", response_model=AIJobAssessmentResponse)
async def ai_analyze_job(
    job_id: int,
    force_reanalyze: bool = Query(False),
    model: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job vacancy not found.")

    profile = get_or_create_user_profile(db)
    assessment = await analyze_job_with_ai(
        db=db,
        job=job,
        profile=profile,
        force_reanalyze=force_reanalyze,
        model_name=model
    )

    return {
        "id": assessment.id,
        "job_id": assessment.job_id,
        "job_hash": assessment.job_hash,
        "match_score": assessment.match_score,
        "application_priority": assessment.application_priority,
        "career_growth_score": assessment.career_growth_score,
        "career_growth_summary": assessment.career_growth_summary,
        "matching_skills": json.loads(assessment.matching_skills or "[]"),
        "missing_requirements": json.loads(assessment.missing_requirements or "[]"),
        "qualification_alignment": json.loads(assessment.qualification_alignment or "[]"),
        "experience_alignment": json.loads(assessment.experience_alignment or "[]"),
        "industry_alignment": json.loads(assessment.industry_alignment or "[]"),
        "visa_relocation_considerations": assessment.visa_relocation_considerations,
        "reasons_to_apply": json.loads(assessment.reasons_to_apply or "[]"),
        "reasons_to_reconsider": json.loads(assessment.reasons_to_reconsider or "[]"),
        "evidence_references": json.loads(assessment.evidence_references or "{}"),
        "model_used": assessment.model_used,
        "engine_used": assessment.engine_used,
        "created_at": assessment.created_at
    }

# 18. Get Existing AI Assessment
@app.get("/api/jobs/{job_id}/ai-assessment", response_model=AIJobAssessmentResponse)
def get_job_ai_assessment(job_id: int, db: Session = Depends(get_db)):
    assessment = db.query(AIJobAssessment).filter(AIJobAssessment.job_id == job_id).first()
    if not assessment or not cached_assessment_is_current(db, db.get(Job, job_id)):
        raise HTTPException(status_code=404, detail="No AI assessment found for this job.")

    return {
        "id": assessment.id,
        "job_id": assessment.job_id,
        "job_hash": assessment.job_hash,
        "match_score": assessment.match_score,
        "application_priority": assessment.application_priority,
        "career_growth_score": assessment.career_growth_score,
        "career_growth_summary": assessment.career_growth_summary,
        "matching_skills": json.loads(assessment.matching_skills or "[]"),
        "missing_requirements": json.loads(assessment.missing_requirements or "[]"),
        "qualification_alignment": json.loads(assessment.qualification_alignment or "[]"),
        "experience_alignment": json.loads(assessment.experience_alignment or "[]"),
        "industry_alignment": json.loads(assessment.industry_alignment or "[]"),
        "visa_relocation_considerations": assessment.visa_relocation_considerations,
        "reasons_to_apply": json.loads(assessment.reasons_to_apply or "[]"),
        "reasons_to_reconsider": json.loads(assessment.reasons_to_reconsider or "[]"),
        "evidence_references": json.loads(assessment.evidence_references or "{}"),
        "model_used": assessment.model_used,
        "engine_used": assessment.engine_used,
        "created_at": assessment.created_at
    }

# 19. AI Usage & Quota Metrics
@app.get("/api/ai/usage", response_model=AIUsageStatsResponse)
def get_ai_usage_stats(db: Session = Depends(get_db)):
    return get_daily_ai_usage(db)


# ==================== PHASE 3 ENDPOINTS ====================

# 20. ATS Keyword Analysis
@app.get("/api/jobs/{job_id}/ats-analysis", response_model=ATSKeywordAnalysisResponse)
def get_job_ats_analysis(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job vacancy not found.")

    profile = get_or_create_user_profile(db)
    profile_dict = format_user_profile_response(profile)

    res = analyze_ats_keywords(job.title, job.description, profile_dict)
    res["job_id"] = job.id
    res["company"] = job.company
    res["title"] = job.title
    return res

# 21. PDF Converter Diagnostics
@app.get("/api/pdf-converter/status")
def get_pdf_converter_status():
    return check_pdf_converter_availability()

# 22. Generate Tailored CV Preview
@app.post("/api/jobs/{job_id}/generate-cv", response_model=TailoredCVContent)
async def generate_cv_for_job(
    job_id: int,
    template_name: str = Query("global_regional_hse"),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job vacancy not found.")

    profile = get_or_create_user_profile(db)
    profile_dict = format_user_profile_response(profile)

    cv_content = await generate_tailored_cv(
        profile=profile_dict,
        job_company=job.company,
        job_title=job.title,
        job_desc=job.description,
        template_name=template_name,
        consent_given=profile.consent_given_for_ai
    )
    return cv_content

# 23. Generate Tailored Cover Letter Preview
@app.post("/api/jobs/{job_id}/generate-cover-letter", response_model=TailoredCoverLetterContent)
async def generate_cover_letter_for_job(
    job_id: int,
    template_name: str = Query("global_regional_hse"),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job vacancy not found.")

    profile = get_or_create_user_profile(db)
    profile_dict = format_user_profile_response(profile)

    cl_content = await generate_tailored_cover_letter(
        profile=profile_dict,
        job_company=job.company,
        job_title=job.title,
        job_location=job.location,
        job_desc=job.description,
        template_name=template_name,
        consent_given=profile.consent_given_for_ai
    )
    return cl_content

# 24. Generate Full Application Package
@app.post("/api/jobs/{job_id}/generate-package", response_model=ApplicationPackageResponse)
def generate_package_for_job(
    job_id: int,
    payload: PackageGenerateRequest,
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job vacancy not found.")

    profile = get_or_create_user_profile(db)
    profile_dict = format_user_profile_response(profile)

    try:
        pkg = create_application_package(
            db=db,
            job=job,
            profile_dict=profile_dict,
            template_name=payload.template_name or "global_regional_hse",
            custom_notes=payload.custom_notes,
            consent_given=profile.consent_given_for_ai,
            force_override=bool(payload.force_override)
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    return format_package_response(pkg)

# 25. List All Packages (Studio Overview)
@app.get("/api/packages", response_model=List[ApplicationPackageResponse])
def list_all_packages(db: Session = Depends(get_db)):
    packages = db.query(ApplicationPackage).order_by(desc(ApplicationPackage.created_at)).all()
    return [format_package_response(p) for p in packages]

# 26. List Packages for specific Job
@app.get("/api/jobs/{job_id}/packages", response_model=List[ApplicationPackageResponse])
def get_packages_for_job(job_id: int, db: Session = Depends(get_db)):
    packages = db.query(ApplicationPackage).filter(
        ApplicationPackage.job_id == job_id
    ).order_by(desc(ApplicationPackage.created_at)).all()
    return [format_package_response(p) for p in packages]

# 27. Get Package Details
@app.get("/api/packages/{package_id}", response_model=ApplicationPackageResponse)
def get_package_by_id(package_id: int, db: Session = Depends(get_db)):
    package = db.query(ApplicationPackage).filter(ApplicationPackage.id == package_id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Application package not found.")
    return format_package_response(package)

# 28. Edit/Update Document Content Draft
@app.put("/api/packages/{package_id}/documents/{document_id}", response_model=GeneratedDocumentResponse)
def update_document(
    package_id: int,
    document_id: int,
    payload: DocumentUpdateRequest,
    db: Session = Depends(get_db)
):
    package = db.query(ApplicationPackage).filter(ApplicationPackage.id == package_id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Application package not found.")

    doc = db.query(GeneratedDocument).filter(
        GeneratedDocument.id == document_id,
        GeneratedDocument.package_id == package_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found in this package.")

    updated_doc = update_document_content(
        db=db,
        package=package,
        document=doc,
        new_content_text=payload.content_text,
        change_summary=payload.change_summary or "Manual user revision"
    )

    versions = [
        {
            "id": v.id,
            "document_id": v.document_id,
            "version_number": v.version_number,
            "change_summary": v.change_summary,
            "created_at": v.created_at
        }
        for v in updated_doc.versions
    ]

    return {
        "id": updated_doc.id,
        "package_id": updated_doc.package_id,
        "doc_type": updated_doc.doc_type,
        "filename": updated_doc.filename,
        "file_path": updated_doc.file_path,
        "content_text": updated_doc.content_text,
        "version_number": updated_doc.version_number,
        "is_approved": updated_doc.is_approved,
        "created_at": updated_doc.created_at,
        "updated_at": updated_doc.updated_at,
        "versions": versions
    }

# 29. Approve Package
@app.post("/api/packages/{package_id}/approve", response_model=ApplicationPackageResponse)
def approve_package_endpoint(
    package_id: int,
    payload: PackageApproveRequest,
    db: Session = Depends(get_db)
):
    package = db.query(ApplicationPackage).filter(ApplicationPackage.id == package_id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Application package not found.")

    approved = approve_package(
        db=db,
        package=package,
        approved_by=payload.approved_by or "Raghunath Reddy",
        notes=payload.approval_notes
    )
    return format_package_response(approved)

# 30. Secure Download for Package ZIP or Documents
@app.get("/api/packages/{package_id}/download")
def download_package_file(
    package_id: int,
    doc_type: Optional[str] = Query(None), # None for full ZIP, or 'cv_docx', 'cv_pdf', 'cover_letter_docx', 'cover_letter_pdf'
    db: Session = Depends(get_db)
):
    package = db.query(ApplicationPackage).filter(ApplicationPackage.id == package_id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Application package not found.")

    if not doc_type or doc_type == "zip":
        if not package.zip_path or not Path(package.zip_path).exists():
            raise HTTPException(status_code=404, detail="ZIP package file not found on disk.")
        target_path = Path(package.zip_path).resolve()
        filename = target_path.name
        media_type = "application/zip"
    else:
        doc = db.query(GeneratedDocument).filter(
            GeneratedDocument.package_id == package_id,
            GeneratedDocument.doc_type == doc_type
        ).first()
        if not doc or not Path(doc.file_path).exists():
            raise HTTPException(status_code=404, detail=f"Document '{doc_type}' not found.")
        target_path = Path(doc.file_path).resolve()
        filename = doc.filename
        if filename.endswith(".docx"):
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif filename.endswith(".pdf"):
            media_type = "application/pdf"
        else:
            media_type = "text/plain"

    # Directory Traversal Protection: verify file resides within PACKAGES_DIR
    resolved_packages_dir = PACKAGES_DIR.resolve()
    try:
        target_path.relative_to(resolved_packages_dir)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: invalid file path.")

    return FileResponse(
        path=str(target_path),
        filename=filename,
        media_type=media_type
    )

# 31. Test Windows Notification
@app.post("/api/notifications/test")
def test_notification():
    success = send_desktop_notification(
        title="🎯 HSE Career Agent - High Match Alert",
        message="Test alert: Global HSE Manager vacancy identified (Score: 92/100). Ready in Application Studio."
    )
    return {
        "success": success,
        "message": "Desktop toast notification dispatched successfully" if success else "Notification attempted via Windows PowerShell."
    }


# Additive Phase 4 routes; legacy endpoints remain available.
from .phase4 import router as phase4_router
app.include_router(phase4_router)
