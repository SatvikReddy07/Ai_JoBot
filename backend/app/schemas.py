from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

# ---- PHASE 2 SCHEMAS ----
class MasterCVResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int
    extracted_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class EmploymentHistoryItem(BaseModel):
    company: str
    role: str
    location: Optional[str] = None
    highlights: List[str] = []
    source: Optional[str] = "verified_profile"

class UserProfileResponse(BaseModel):
    id: int
    name: str
    current_role: str
    current_company: str
    location: str
    experience_years: int
    summary: Optional[str] = None
    employment_history: List[EmploymentHistoryItem] = []
    qualifications: List[str] = []
    skills: List[str] = []
    certifications: List[str] = []
    achievements: List[str] = []
    target_countries: List[str] = []
    target_titles: List[str] = []
    consent_given_for_ai: bool = False
    last_updated_at: datetime
    cv: Optional[MasterCVResponse] = None

    model_config = ConfigDict(from_attributes=True)


class CVUploadResponse(BaseModel):
    message: str
    cv_id: int
    filename: str
    profile: UserProfileResponse

    model_config = ConfigDict(from_attributes=True)

class UserProfileUpdate(BaseModel):

    name: Optional[str] = None
    current_role: Optional[str] = None
    current_company: Optional[str] = None
    location: Optional[str] = None
    experience_years: Optional[int] = None
    summary: Optional[str] = None
    employment_history: Optional[List[EmploymentHistoryItem]] = None
    qualifications: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    certifications: Optional[List[str]] = None
    achievements: Optional[List[str]] = None
    target_countries: Optional[List[str]] = None
    target_titles: Optional[List[str]] = None
    consent_given_for_ai: Optional[bool] = None

class UserConsentToggle(BaseModel):
    consent_given: bool

class AIJobAssessmentResponse(BaseModel):
    id: int
    job_id: int
    job_hash: str
    match_score: int
    application_priority: str
    career_growth_score: int
    career_growth_summary: Optional[str] = None
    matching_skills: List[str] = []
    missing_requirements: List[str] = []
    qualification_alignment: List[str] = []
    experience_alignment: List[str] = []
    industry_alignment: List[str] = []
    visa_relocation_considerations: Optional[str] = None
    reasons_to_apply: List[str] = []
    reasons_to_reconsider: List[str] = []
    evidence_references: Dict[str, Any] = {}
    model_used: str
    engine_used: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AIUsageStatsResponse(BaseModel):
    daily_used: int
    daily_limit: int
    remaining: int
    cached_today: int
    date: str
    model: str
    api_key_configured: bool

# ---- JOB SCHEMAS ----
class JobBase(BaseModel):
    source: str
    source_job_id: str
    company: str
    title: str
    normalized_title: Optional[str] = None
    location: str
    city: Optional[str] = None
    country: Optional[str] = None
    employment_type: str = "Unknown"
    is_permanent_fulltime: bool = False
    description: str
    raw_description_html: Optional[str] = None
    url: str
    posted_date: Optional[datetime] = None

class JobResponse(BaseModel):
    id: int
    source: str
    source_job_id: str
    company: str
    title: str
    normalized_title: Optional[str] = None
    location: str
    city: Optional[str] = None
    country: Optional[str] = None
    employment_type: str
    is_permanent_fulltime: bool
    description: str
    raw_description_html: Optional[str] = None
    url: str
    posted_date: Optional[datetime] = None
    discovered_at: datetime
    last_verified_at: datetime
    is_active: bool
    match_score: int
    match_level: str
    match_reasons: Optional[List[str]] = []
    matching_qualifications: Optional[List[str]] = []
    matching_experience: Optional[List[str]] = []
    matching_skills: Optional[List[str]] = []
    missing_requirements: Optional[List[str]] = []
    location_suitability: Optional[str] = None
    sponsorship_status: str
    application_status: str
    application_notes: Optional[str] = None
    is_saved: bool
    ai_assessment: Optional[AIJobAssessmentResponse] = None

    model_config = ConfigDict(from_attributes=True)

class JobListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[JobResponse]

class JobStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None

class JobSaveToggle(BaseModel):
    is_saved: bool

# ---- EMPLOYER BOARD SCHEMAS ----
class EmployerBoardBase(BaseModel):
    company_name: str
    platform: str  # 'greenhouse' or 'lever'
    board_token: str
    is_enabled: bool = True

class EmployerBoardCreate(EmployerBoardBase):
    pass

class EmployerBoardUpdate(BaseModel):
    company_name: Optional[str] = None
    platform: Optional[str] = None
    board_token: Optional[str] = None
    is_enabled: Optional[bool] = None

class EmployerBoardResponse(EmployerBoardBase):
    id: int
    created_at: datetime
    last_searched_at: Optional[datetime] = None
    last_status: Optional[str] = None
    last_job_count: int = 0

    model_config = ConfigDict(from_attributes=True)

# ---- SEARCH PREFERENCE & SETTINGS ----
class ScoringWeights(BaseModel):
    experience_seniority: int = 25
    hse_technical_skills: int = 25
    qualifications: int = 15
    industry_relevance: int = 15
    location_international: int = 15
    employment_preferences: int = 5

class SettingsResponse(BaseModel):
    profile_name: str
    profile_current_role: str
    profile_experience_years: int
    target_countries: List[str]
    target_titles: List[str]
    min_match_score: int
    scoring_weights: ScoringWeights
    auto_search_hour: int
    auto_search_minute: int
    updated_at: datetime
    gemini_model: Optional[str] = "gemini-2.5-flash"
    ai_daily_limit: Optional[int] = 50
    api_key_configured: Optional[bool] = False

class SettingsUpdate(BaseModel):
    profile_name: Optional[str] = None
    profile_current_role: Optional[str] = None
    profile_experience_years: Optional[int] = None
    target_countries: Optional[List[str]] = None
    target_titles: Optional[List[str]] = None
    min_match_score: Optional[int] = None
    scoring_weights: Optional[ScoringWeights] = None
    auto_search_hour: Optional[int] = None
    auto_search_minute: Optional[int] = None
    gemini_model: Optional[str] = None
    ai_daily_limit: Optional[int] = None

# ---- SEARCH RUN & HISTORY ----
class SearchRunResponse(BaseModel):
    status: str
    boards_searched: int
    jobs_found: int
    jobs_new: int
    jobs_updated: int
    message: str

class SearchHistoryResponse(BaseModel):
    id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    jobs_found: int
    jobs_new: int
    jobs_updated: int
    boards_searched: int
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# ---- DASHBOARD STATS ----
class DashboardStatsResponse(BaseModel):
    total_jobs: int
    new_jobs_today: int
    excellent_matches: int
    strong_matches: int
    saved_opportunities: int
    active_applications: int
    last_successful_search: Optional[datetime] = None
    ai_analyzed_count: int = 0


# ==================== PHASE 3 SCHEMAS ====================

class TailoredCVContent(BaseModel):
    name: str = "Raghunath Reddy"
    headline: str = "Global SHE & Security Manager"
    contact_email: str = "raghunath.hse@gmail.com"
    contact_phone: str = "+91 98490 00000"
    contact_location: str = "Hyderabad, India"
    contact_linkedin: str = "linkedin.com/in/raghunath-reddy-hse"
    summary: str
    core_competencies: List[str] = []
    employment_history: List[EmploymentHistoryItem] = []
    education: List[str] = []
    certifications: List[str] = []
    key_achievements: List[str] = []
    template_name: str = "global_regional_hse"
    target_job_title: str
    target_company: str
    generation_method: str = "rules_fallback"  # 'ai' or 'rules_fallback'
    evidence_notes: Dict[str, Any] = {}


class TailoredCoverLetterContent(BaseModel):
    candidate_name: str = "Raghunath Reddy"
    candidate_contact: str = "Hyderabad, India | +91 98490 00000 | raghunath.hse@gmail.com"
    date_str: str
    hiring_manager: str = "Hiring Team"
    company_name: str
    job_title: str
    salutation: str = "Dear Hiring Team,"
    body_paragraphs: List[str] = []
    sign_off: str = "Sincerely,\nRaghunath Reddy"
    generation_method: str = "rules_fallback"


class ATSMatchedKeyword(BaseModel):
    keyword: str
    category: str
    evidence: str


class ATSMissingKeyword(BaseModel):
    keyword: str
    category: str
    impact: str


class ATSKeywordAnalysisResponse(BaseModel):
    job_id: int
    company: str
    title: str
    overall_coverage_pct: float
    matched_keywords: List[ATSMatchedKeyword] = []
    missing_keywords: List[ATSMissingKeyword] = []
    legitimate_suggestions: List[str] = []
    disclaimer: str = "Internal coverage indicator based on candidate profile evidence, not a guarantee of employer ATS scoring."


class DocumentVersionResponse(BaseModel):
    id: int
    document_id: int
    version_number: int
    change_summary: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GeneratedDocumentResponse(BaseModel):
    id: int
    package_id: int
    doc_type: str
    filename: str
    file_path: str
    content_text: Optional[str] = None
    version_number: int
    is_approved: bool
    created_at: datetime
    updated_at: datetime
    versions: List[DocumentVersionResponse] = []

    model_config = ConfigDict(from_attributes=True)


class DocumentApprovalResponse(BaseModel):
    id: int
    package_id: int
    approved_by: str
    version_approved: int
    approval_notes: Optional[str] = None
    approved_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationPackageResponse(BaseModel):
    id: int
    job_id: int
    job_title: str
    company: str
    job_location: str
    template_name: str
    status: str
    generation_method: str
    ats_match_score: float
    ats_analysis: Dict[str, Any] = {}
    notes: Optional[str] = None
    has_zip: bool
    created_at: datetime
    updated_at: datetime
    documents: List[GeneratedDocumentResponse] = []
    approvals: List[DocumentApprovalResponse] = []

    model_config = ConfigDict(from_attributes=True)


class PackageGenerateRequest(BaseModel):
    template_name: Optional[str] = "global_regional_hse"
    custom_notes: Optional[str] = None
    force_override: Optional[bool] = False


class DocumentUpdateRequest(BaseModel):
    content_text: str
    change_summary: Optional[str] = "Manual candidate revision"


class PackageApproveRequest(BaseModel):
    approved_by: Optional[str] = "Raghunath Reddy"
    approval_notes: Optional[str] = "Approved tailored application package"


class NotificationConfig(BaseModel):
    enabled: bool = True
    min_score: int = 85
    quiet_hours_enabled: bool = True
    quiet_hours_start: int = 22
    quiet_hours_end: int = 7


# ==================== PHASE 4 SCHEMAS ====================

# -- Eligibility Engine --
class EligibilityCheck(BaseModel):
    category: str  # occupational_relevance, seniority, technical_qualifications, education, certifications, location, work_authorization, visa_sponsorship, language, licenses, employment_type, closing_date
    status: str  # met, not_met, unknown, requires_review
    detail: str
    is_mandatory: bool = False

class EligibilityAssessmentResponse(BaseModel):
    job_id: int
    company: str
    title: str
    overall_status: str  # ready, requires_review, missing_info, not_suitable
    checks: List[EligibilityCheck] = []
    met_count: int = 0
    not_met_count: int = 0
    unknown_count: int = 0
    recommendation: str = ""

# -- Job Application --
class JobApplicationCreate(BaseModel):
    job_id: int
    notes: Optional[str] = None

class JobApplicationStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None
    confirmation_reference: Optional[str] = None
    date_submitted: Optional[datetime] = None
    follow_up_date: Optional[datetime] = None

class JobApplicationResponse(BaseModel):
    id: int
    job_id: int
    package_id: Optional[int] = None
    status: str
    eligibility_status: str
    eligibility_details: Optional[Dict[str, Any]] = None
    application_url: Optional[str] = None
    application_portal: Optional[str] = None
    submission_method: Optional[str] = None
    cv_version: Optional[str] = None
    cover_letter_version: Optional[str] = None
    date_prepared: Optional[datetime] = None
    date_submitted: Optional[datetime] = None
    confirmation_reference: Optional[str] = None
    user_approved: bool = False
    user_approved_at: Optional[datetime] = None
    approval_notes: Optional[str] = None
    application_questions: Optional[Dict[str, Any]] = None
    follow_up_date: Optional[datetime] = None
    follow_up_notes: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    # Denormalized job info for display
    job_title: Optional[str] = None
    job_company: Optional[str] = None
    job_location: Optional[str] = None
    job_match_score: Optional[int] = None
    job_sponsorship: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ApplicationApprovalRequest(BaseModel):
    approval_notes: Optional[str] = "User approved for application preparation"

class SubmissionRecordRequest(BaseModel):
    confirmation_reference: Optional[str] = None
    submission_method: Optional[str] = "manual_upload"
    notes: Optional[str] = None

# -- Recruiter Contacts --
class RecruiterContactCreate(BaseModel):
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    contact_type: str = "recruiter"
    notes: Optional[str] = None

class RecruiterContactResponse(BaseModel):
    id: int
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    contact_type: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# -- Recruiter Outreach --
class OutreachGenerateRequest(BaseModel):
    application_id: Optional[int] = None
    contact_id: Optional[int] = None
    message_type: str = "initial_outreach"  # initial_outreach, follow_up, referral_request, thank_you
    channel: str = "linkedin"  # linkedin, email
    custom_notes: Optional[str] = None

class RecruiterOutreachResponse(BaseModel):
    id: int
    application_id: Optional[int] = None
    contact_id: Optional[int] = None
    message_type: str
    channel: str
    subject: Optional[str] = None
    message_body: str
    is_approved: bool
    is_sent: bool
    sent_at: Optional[datetime] = None
    response_received: bool
    response_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# -- Follow-up Reminders --
class ReminderCreate(BaseModel):
    application_id: Optional[int] = None
    reminder_type: str = "follow_up"
    title: str
    description: Optional[str] = None
    due_date: datetime

class ReminderResponse(BaseModel):
    id: int
    application_id: Optional[int] = None
    reminder_type: str
    title: str
    description: Optional[str] = None
    due_date: datetime
    is_completed: bool
    completed_at: Optional[datetime] = None
    is_dismissed: bool
    snooze_until: Optional[datetime] = None
    created_at: datetime
    # Denormalized for display
    job_title: Optional[str] = None
    company: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# -- Application Control Center Dashboard --
class ApplicationControlCenterStats(BaseModel):
    total_applications: int = 0
    shortlisted: int = 0
    ready_for_application: int = 0
    in_progress: int = 0
    submitted: int = 0
    follow_up_due: int = 0
    interviews_scheduled: int = 0
    offers_received: int = 0
    rejected: int = 0
    withdrawn: int = 0
    pending_reminders: int = 0
    overdue_reminders: int = 0

class PortalInfo(BaseModel):
    name: str
    supported: bool
    features: List[str] = []
    limitations: List[str] = []
