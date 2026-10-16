import datetime
from sqlalchemy import (
    Column, Integer, Float, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from .database import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), nullable=False, index=True)  # 'greenhouse', 'lever'
    source_job_id = Column(String(100), nullable=False, index=True)
    company = Column(String(150), nullable=False, index=True)
    title = Column(String(255), nullable=False, index=True)
    normalized_title = Column(String(255), nullable=True)
    location = Column(String(255), nullable=False)
    city = Column(String(100), nullable=True, index=True)
    country = Column(String(100), nullable=True, index=True)
    employment_type = Column(String(100), nullable=False, default="Unknown")
    is_permanent_fulltime = Column(Boolean, default=False)
    description = Column(Text, nullable=False)
    raw_description_html = Column(Text, nullable=True)
    url = Column(String(500), nullable=False)
    posted_date = Column(DateTime, nullable=True)
    discovered_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_verified_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Scoring & Evaluation (Rules-based baseline)
    match_score = Column(Integer, default=0, index=True)
    match_level = Column(String(50), default="Low Match", index=True)
    match_reasons = Column(Text, nullable=True)             # JSON list
    matching_qualifications = Column(Text, nullable=True)  # JSON list
    matching_experience = Column(Text, nullable=True)      # JSON list
    matching_skills = Column(Text, nullable=True)          # JSON list
    missing_requirements = Column(Text, nullable=True)     # JSON list
    location_suitability = Column(String(255), nullable=True)
    sponsorship_status = Column(String(50), default="Unknown")  # 'Confirmed', 'Not Supported', 'Unknown'

    # Application Tracker
    application_status = Column(String(50), default="Discovered", index=True)
    application_notes = Column(Text, nullable=True)
    is_saved = Column(Boolean, default=False, index=True)

    # Relationships
    history = relationship("ApplicationHistory", back_populates="job", cascade="all, delete-orphan")
    ai_assessment = relationship("AIJobAssessment", back_populates="job", uselist=False, cascade="all, delete-orphan")
    packages = relationship("ApplicationPackage", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("source", "source_job_id", name="uq_source_source_job_id"),
    )

class EmployerBoard(Base):
    __tablename__ = "employer_boards"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(150), nullable=False)
    platform = Column(String(50), nullable=False)  # 'greenhouse' or 'lever'
    board_token = Column(String(100), nullable=False, unique=True, index=True)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_searched_at = Column(DateTime, nullable=True)
    last_status = Column(String(50), nullable=True)
    last_job_count = Column(Integer, default=0)

class SearchPreference(Base):
    __tablename__ = "search_preferences"

    id = Column(Integer, primary_key=True)
    profile_name = Column(String(100), default="Raghunath Reddy")
    profile_current_role = Column(String(150), default="Global SHE & Security Manager")
    profile_experience_years = Column(Integer, default=18)
    target_countries = Column(Text, nullable=False)  # JSON list
    target_titles = Column(Text, nullable=False)     # JSON list
    min_match_score = Column(Integer, default=50)
    scoring_weights = Column(Text, nullable=False)   # JSON dict
    auto_search_hour = Column(Integer, default=8)
    auto_search_minute = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="running")  # 'running', 'success', 'failed'
    jobs_found = Column(Integer, default=0)
    jobs_new = Column(Integer, default=0)
    jobs_updated = Column(Integer, default=0)
    boards_searched = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

class ApplicationHistory(Base):
    __tablename__ = "application_history"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True)
    changed_at = Column(DateTime, default=datetime.datetime.utcnow)

    job = relationship("Job", back_populates="history")

# ==================== PHASE 2 MODELS ====================

class MasterCV(Base):
    __tablename__ = "master_cvs"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)  # 'pdf' or 'docx'
    stored_path = Column(String(500), nullable=False)
    raw_text = Column(Text, nullable=False)
    file_size = Column(Integer, default=0)
    extracted_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), default="Raghunath Reddy")
    current_role = Column(String(150), default="Global SHE & Security Manager")
    current_company = Column(String(150), default="dsm-firmenich")
    location = Column(String(150), default="Hyderabad, India")
    experience_years = Column(Integer, default=18)
    summary = Column(Text, nullable=True)
    employment_history = Column(Text, nullable=False)  # JSON list of roles & organizations
    qualifications = Column(Text, nullable=False)      # JSON list of degrees
    skills = Column(Text, nullable=False)              # JSON list of HSE competencies
    certifications = Column(Text, nullable=False)      # JSON list of certifications
    achievements = Column(Text, nullable=False)        # JSON list of major accomplishments
    target_countries = Column(Text, nullable=False)    # JSON list of target destinations
    target_titles = Column(Text, nullable=False)       # JSON list of target positions
    consent_given_for_ai = Column(Boolean, default=False)  # Strict privacy consent flag
    last_updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    cv_id = Column(Integer, ForeignKey("master_cvs.id"), nullable=True)

    cv = relationship("MasterCV")

class AIJobAssessment(Base):
    __tablename__ = "ai_job_assessments"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, unique=True, index=True)
    job_hash = Column(String(64), nullable=False, index=True)  # SHA-256 for change detection & caching
    match_score = Column(Integer, default=0)
    application_priority = Column(String(20), default="Medium")  # 'High', 'Medium', 'Low'
    career_growth_score = Column(Integer, default=0)
    career_growth_summary = Column(Text, nullable=True)
    matching_skills = Column(Text, nullable=True)              # JSON list
    missing_requirements = Column(Text, nullable=True)         # JSON list
    qualification_alignment = Column(Text, nullable=True)      # JSON list / string
    experience_alignment = Column(Text, nullable=True)         # JSON list / string
    industry_alignment = Column(Text, nullable=True)           # JSON list / string
    visa_relocation_considerations = Column(Text, nullable=True)
    reasons_to_apply = Column(Text, nullable=True)             # JSON list
    reasons_to_reconsider = Column(Text, nullable=True)        # JSON list
    evidence_references = Column(Text, nullable=True)          # JSON dict / list
    model_used = Column(String(50), default="gemini-2.5-flash")
    engine_used = Column(String(50), default="ai")             # 'ai' or 'rules_fallback'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    raw_response_json = Column(Text, nullable=True)

    job = relationship("Job", back_populates="ai_assessment")

class AIUsageLog(Base):
    __tablename__ = "ai_usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    job_id = Column(Integer, nullable=True)
    model = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)  # 'success', 'rate_limited', 'failed', 'cached'
    daily_date = Column(String(20), nullable=False, index=True)  # YYYY-MM-DD


# ==================== PHASE 3 MODELS ====================

class ApplicationPackage(Base):
    __tablename__ = "application_packages"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    template_name = Column(String(100), default="global_regional_hse")
    status = Column(String(50), default="draft", index=True)  # 'draft', 'in_review', 'approved'
    package_dir = Column(String(500), nullable=False)
    zip_path = Column(String(500), nullable=True)
    generation_method = Column(String(50), default="rules_fallback")  # 'ai' or 'rules_fallback'
    ats_match_score = Column(Float, default=0.0)
    ats_analysis_json = Column(Text, default="{}")  # JSON with matched/missing keywords, suggestions
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    job = relationship("Job", back_populates="packages")
    documents = relationship("GeneratedDocument", back_populates="package", cascade="all, delete-orphan")
    approvals = relationship("DocumentApproval", back_populates="package", cascade="all, delete-orphan")
    audit_logs = relationship("GenerationAuditLog", back_populates="package", cascade="all, delete-orphan")


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("application_packages.id"), nullable=False, index=True)
    doc_type = Column(String(50), nullable=False, index=True)  # 'cv_docx', 'cv_pdf', 'cover_letter_docx', 'cover_letter_pdf', 'job_description', 'checklist', 'metadata'
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    content_text = Column(Text, nullable=True)  # JSON or plain text body
    version_number = Column(Integer, default=1)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    package = relationship("ApplicationPackage", back_populates="documents")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("generated_documents.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    content_text = Column(Text, nullable=False)
    file_path = Column(String(500), nullable=True)
    change_summary = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    document = relationship("GeneratedDocument", back_populates="versions")


class DocumentApproval(Base):
    __tablename__ = "document_approvals"

    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("application_packages.id"), nullable=False, index=True)
    approved_by = Column(String(100), default="Raghunath Reddy")
    version_approved = Column(Integer, default=1)
    approval_notes = Column(Text, nullable=True)
    approved_at = Column(DateTime, default=datetime.datetime.utcnow)

    package = relationship("ApplicationPackage", back_populates="approvals")


class GenerationAuditLog(Base):
    __tablename__ = "generation_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("application_packages.id"), nullable=False, index=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    engine_used = Column(String(50), default="rules_fallback")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    package = relationship("ApplicationPackage", back_populates="audit_logs")


class DesktopNotificationLog(Base):
    __tablename__ = "desktop_notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    match_score = Column(Integer, nullable=False)
    notification_type = Column(String(50), default="high_match")
    status = Column(String(50), default="sent")
    notified_at = Column(DateTime, default=datetime.datetime.utcnow)

