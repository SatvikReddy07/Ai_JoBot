"""Local application preparation APIs. No network calls or submission capability."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .database import get_db
from .models import (Job, UserProfile, ApplicationPackage, GeneratedDocument, JobApplication,
    ApplicationHistory, ApplicationEvent, RecruiterContact, RecruiterOutreach, FollowUpReminder)
from ..services.eligibility_service import assess_eligibility
from ..services.portal_service import portal_info, validate_portal_url, vacancy_key

router = APIRouter(prefix="/api/phase4", tags=["Application Control Center"])
STAGES = {"discovered", "shortlisted", "documents_prepared", "ready_for_review", "in_progress",
          "submitted", "follow_up_due", "interview_scheduled", "rejected", "offer_received", "withdrawn"}
TRANSITIONS = {
 "discovered": {"shortlisted", "withdrawn"},
 "shortlisted": {"documents_prepared", "withdrawn", "rejected"},
 "documents_prepared": {"ready_for_review", "withdrawn", "rejected"},
 "ready_for_review": {"in_progress", "documents_prepared", "withdrawn", "rejected"},
 "in_progress": {"documents_prepared", "withdrawn", "rejected"},
 "submitted": {"follow_up_due", "interview_scheduled", "rejected", "withdrawn", "offer_received"},
 "follow_up_due": {"interview_scheduled", "rejected", "withdrawn", "offer_received"},
 "interview_scheduled": {"rejected", "offer_received", "withdrawn"},
 "offer_received": {"withdrawn"}, "rejected": set(), "withdrawn": set()
}

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class CreateApplication(StrictModel):
    job_id: int
    notes: str = Field(default="", max_length=5000)

class ReviewCheck(StrictModel):
    category: str
    status: Literal["met", "not_met", "unknown", "requires_review"]
    evidence: str = Field(min_length=5, max_length=2000)

class EligibilityReview(StrictModel):
    checks: list[ReviewCheck]

class Question(StrictModel):
    question: str = Field(min_length=1, max_length=1000)
    answer: str = Field(default="", max_length=5000)
    verified: bool = False
    mandatory: bool = True

class PrepareApplication(StrictModel):
    package_id: int
    cv_document_id: int
    cover_letter_document_id: int
    application_url: str = Field(max_length=500)
    questions: list[Question] = Field(default_factory=list, max_length=100)
    verified_fields: dict[str, str] = Field(default_factory=dict)
    profile_reviewed: bool
    official_url_verified: bool

class Approve(StrictModel):
    acknowledge_unknowns: bool = False
    notes: str = Field(min_length=5, max_length=3000)

class StageUpdate(StrictModel):
    status: str
    notes: str = Field(default="", max_length=5000)

class Submission(StrictModel):
    confirmation_reference: str = Field(min_length=3, max_length=500)
    manually_submitted: bool
    follow_up_enabled: bool = True
    follow_up_days: int = Field(default=7, ge=1, le=365)

class ContactCreate(StrictModel):
    name: str = Field(min_length=1, max_length=200)
    company: str = Field(default="", max_length=200)
    email: str = Field(default="", max_length=255)
    linkedin_url: str = Field(default="", max_length=500)
    title: str = Field(default="", max_length=200)

class OutreachCreate(StrictModel):
    contact_id: int | None = None
    kind: Literal["recruiter", "hiring_manager", "talent_acquisition", "referral", "follow_up"] = "recruiter"
    channel: Literal["linkedin", "email"] = "linkedin"

class OutreachEdit(StrictModel):
    message_body: str = Field(min_length=1, max_length=10000)
    subject: str = Field(default="", max_length=255)
    approved: bool = False
    manually_sent: bool = False

class ReminderInput(StrictModel):
    title: str = Field(min_length=1, max_length=255)
    due_date: datetime
    reminder_type: Literal["follow_up", "deadline", "interview_prep", "document_request", "completion"] = "follow_up"

class ReminderUpdate(StrictModel):
    due_date: datetime | None = None
    is_completed: bool = False
    is_dismissed: bool = False


def fail(detail, code=409):
    raise HTTPException(code, detail)

def profile_for(db):
    p = db.query(UserProfile).first()
    if not p: fail("Create and review your career profile first.")
    return p

def find_application(db, application_id):
    a = db.get(JobApplication, application_id)
    if not a: fail("Application not found.", 404)
    return a

def event(db, a, action, details):
    db.add(ApplicationEvent(application_id=a.id, action=action, details=json.dumps(details, default=str)))
    a.updated_at = datetime.utcnow()

def fingerprint(job, profile):
    fields = {c.name: getattr(profile, c.name) for c in profile.__table__.columns if c.name not in {"consent_given_for_ai"}}
    vacancy = {name: getattr(job, name) for name in (
        "source", "source_job_id", "company", "title", "location", "city", "country",
        "employment_type", "is_permanent_fulltime", "description", "url", "is_active")}
    return hashlib.sha256(json.dumps([vacancy, fields], sort_keys=True, default=str).encode()).hexdigest()

def assessment(db, job, a=None):
    p = profile_for(db)
    base = assess_eligibility(job, p)
    if base["overall_status"] == "not_eligible": return base
    if a and a.eligibility_details:
        saved = json.loads(a.eligibility_details)
        if saved.get("fingerprint") == fingerprint(job, p):
            return saved["assessment"]
    return base

def set_stage(db, a, stage, notes=""):
    previous = a.status
    a.status = stage
    a.job.application_status = stage.replace("_", " ").title()
    a.job.is_saved = True
    db.add(ApplicationHistory(job_id=a.job_id, previous_status=previous, new_status=stage, notes=notes))
    event(db, a, "status_changed", dict(previous=previous, status=stage, notes=notes))

def serialize(a):
    data = {c.name: getattr(a, c.name) for c in a.__table__.columns}
    data.pop("confirmation_screenshot_path", None)
    data["preparation"] = json.loads(data.pop("application_questions_json") or "{}")
    data["eligibility_details"] = json.loads(data["eligibility_details"]) if data["eligibility_details"] else None
    data.update(job_title=a.job.title, job_company=a.job.company, job_location=a.job.location,
        country=a.job.country, match_score=a.job.match_score, sponsorship_status=a.job.sponsorship_status)
    return data

def snapshot(db, a):
    prep = json.loads(a.application_questions_json or "{}")
    docs = [db.get(GeneratedDocument, prep.get(key)) for key in ("cv_document_id", "cover_letter_document_id")]
    if any(d is None or d.package_id != a.package_id or not d.is_approved for d in docs):
        fail("Selected documents must belong to the approved package.")
    if not a.package or a.package.status != "approved" or a.package.job_id != a.job_id:
        fail("Approve the selected package in Application Studio first.")
    from ..services.package_service import PACKAGES_DIR
    from pathlib import Path
    files = []
    for d in docs:
        path = Path(d.file_path).resolve()
        if not path.is_relative_to(PACKAGES_DIR.resolve()) or not path.is_file():
            fail("Selected document is unavailable. Regenerate this package in Application Studio.")
        files.append((d.id, d.version_number, hashlib.sha256(path.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps([files, fingerprint(a.job, profile_for(db)),
        a.application_url, prep.get("questions"), prep.get("verified_fields"),
        a.eligibility_details], sort_keys=True, default=str).encode()).hexdigest()

def ensure_approved(db, a):
    if assess_eligibility(a.job, profile_for(db))["overall_status"] == "not_eligible":
        fail("The vacancy is no longer eligible or active. Recheck the original listing.")
    prep = json.loads(a.application_questions_json or "{}")
    if not a.user_approved or prep.get("approval_digest") != snapshot(db, a):
        fail("Application approval is missing or stale. Review and approve again.")

@router.get("/queue")
def queue(db: Session = Depends(get_db)):
    p = profile_for(db)
    applications = {a.job_id: a for a in db.query(JobApplication).all()}
    items = []
    for job in db.query(Job).filter(Job.is_active.is_(True)).all():
        a = applications.get(job.id)
        eligibility = assessment(db, job, a)
        if eligibility["overall_status"] == "not_eligible": continue
        items.append(dict(job_id=job.id, company=job.company, title=job.title, country=job.country,
            location=job.location, url=job.url, match_score=eligibility["match_score"],
            sponsorship_status=eligibility["sponsorship_status"], eligibility=eligibility,
            application=serialize(a) if a else None))
    return sorted(items, key=lambda j: j["match_score"], reverse=True)

@router.get("/jobs/{job_id}/eligibility")
def job_eligibility(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job: fail("Job not found.", 404)
    return assess_eligibility(job, profile_for(db))

@router.get("/applications")
def applications(db: Session = Depends(get_db)):
    return [serialize(a) for a in db.query(JobApplication).order_by(JobApplication.updated_at.desc()).all()]

@router.post("/applications", status_code=201)
def create_application(payload: CreateApplication, db: Session = Depends(get_db)):
    job = db.get(Job, payload.job_id)
    if not job: fail("Job not found.", 404)
    # Lock before duplicate lookup so concurrent source duplicates cannot both insert.
    from sqlalchemy import text
    if db.bind.dialect.name == "sqlite":
        db.rollback()
        db.execute(text("BEGIN IMMEDIATE"))
        job = db.get(Job, payload.job_id)
    for existing in db.query(JobApplication).all():
        if existing.job_id == job.id or vacancy_key(existing.job.url) == vacancy_key(job.url):
            fail("An application already exists for this vacancy.")
    if (job.application_status or "").lower() in {"applied", "submitted", "interview", "offer"}:
        fail("Legacy tracker records an application. Review history before creating a duplicate.")
    eligibility = assess_eligibility(job, profile_for(db))
    if eligibility["overall_status"] == "not_eligible": fail("This job is excluded by eligibility checks.")
    a = JobApplication(job_id=job.id, status="shortlisted", eligibility_status=eligibility["overall_status"],
        application_url=job.url, notes=payload.notes)
    db.add(a)
    try: db.flush()
    except IntegrityError:
        db.rollback(); fail("An application already exists for this vacancy.")
    set_stage(db, a, "shortlisted", payload.notes)
    db.commit()
    return serialize(a)

@router.post("/applications/{application_id}/eligibility-review")
def review_eligibility(application_id: int, payload: EligibilityReview, db: Session = Depends(get_db)):
    a = find_application(db, application_id)
    if a.date_submitted: fail("Submitted application eligibility is retained as historical evidence.")
    result = assessment(db, a.job, a)
    if assess_eligibility(a.job, profile_for(db))["overall_status"] == "not_eligible": fail("Occupational and expired-job exclusions cannot be overridden.")
    edits = {c.category: c for c in payload.checks}
    valid = {c["category"] for c in result["checks"]}
    if set(edits) - valid: fail("Unknown eligibility category.", 422)
    for c in result["checks"]:
        edit = edits.get(c["category"])
        if edit:
            if c["category"] in {"occupational_relevance", "closing_date"}: fail("This check must be derived from the listing.")
            c.update(status=edit.status, detail=edit.evidence, source="user_confirmed")
    mandatory = [c for c in result["checks"] if c["is_mandatory"]]
    result["overall_status"] = ("not_eligible" if any(c["status"] == "not_met" for c in mandatory) else
        "suitable" if all(c["status"] == "met" for c in mandatory) else "requires_review")
    a.eligibility_status = result["overall_status"]
    a.eligibility_details = json.dumps(dict(fingerprint=fingerprint(a.job, profile_for(db)), assessment=result))
    a.user_approved = False
    event(db, a, "eligibility_reviewed", payload.model_dump())
    db.commit()
    return result

@router.put("/applications/{application_id}/prepare")
def prepare(application_id: int, payload: PrepareApplication, db: Session = Depends(get_db)):
    a = find_application(db, application_id)
    if a.status not in {"shortlisted", "documents_prepared", "ready_for_review", "in_progress"}: fail("Cannot replace documents after submission or closure.")
    if not payload.profile_reviewed or not payload.official_url_verified: fail("Review candidate facts and verify employer portal first.")
    validate_url_or_fail(payload.application_url)
    package = db.get(ApplicationPackage, payload.package_id)
    if not package or package.job_id != a.job_id: fail("Package belongs to another vacancy.")
    cv = db.get(GeneratedDocument, payload.cv_document_id)
    letter = db.get(GeneratedDocument, payload.cover_letter_document_id)
    if not cv or cv.doc_type not in {"cv_docx", "cv_pdf"}: fail("Select a CV document.")
    if not letter or letter.doc_type not in {"cover_letter_docx", "cover_letter_pdf"}: fail("Select a cover-letter document.")
    if set(payload.verified_fields) - {"name", "email", "phone", "location", "current_company", "current_role"}:
        fail("Unsupported form field. Sensitive eligibility questions must be reviewed separately.", 422)
    if any(len(v) > 1000 for v in payload.verified_fields.values()): fail("Form field too long.", 422)
    result = assessment(db, a.job, a)
    if result["overall_status"] == "not_eligible": fail("Eligibility check excludes this application.")
    a.package_id = package.id
    a.application_url = payload.application_url
    a.application_portal = portal_info(a.application_url)["name"]
    a.application_questions_json = json.dumps(payload.model_dump())
    a.cv_version = f"{cv.id}:v{cv.version_number}"
    a.cover_letter_version = f"{letter.id}:v{letter.version_number}"
    snapshot(db, a)  # verifies approval and file containment before persisting changes
    a.user_approved = False
    a.user_approved_at = None
    a.date_prepared = datetime.utcnow()
    a.eligibility_status = result["overall_status"]
    set_stage(db, a, "documents_prepared", "Selected document versions; approval reset.")
    event(db, a, "prepared", payload.model_dump())
    db.commit()
    return serialize(a)

def validate_url_or_fail(url):
    try: validate_portal_url(url)
    except ValueError as exc: fail(str(exc), 422)

@router.post("/applications/{application_id}/approve")
def approve(application_id: int, payload: Approve, db: Session = Depends(get_db)):
    a = find_application(db, application_id)
    if a.status not in {"documents_prepared", "ready_for_review"}: fail("Prepare documents before approval.")
    prep = json.loads(a.application_questions_json or "{}")
    if any(q["mandatory"] and (not q["answer"].strip() or not q["verified"]) for q in prep.get("questions", [])):
        fail("Answer and verify every mandatory application question.")
    result = assessment(db, a.job, a)
    if result["overall_status"] == "not_eligible": fail("Not eligible.")
    if result["overall_status"] != "suitable" and not payload.acknowledge_unknowns:
        fail("Review and explicitly acknowledge unresolved eligibility information.")
    prep["approval_digest"] = snapshot(db, a)
    a.application_questions_json = json.dumps(prep)
    a.user_approved = True
    a.user_approved_at = datetime.utcnow()
    a.approval_notes = payload.notes
    set_stage(db, a, "ready_for_review", payload.notes)
    event(db, a, "preparation_approved", payload.model_dump())
    db.commit()
    return serialize(a)

@router.post("/applications/{application_id}/start")
def start(application_id: int, db: Session = Depends(get_db)):
    a = find_application(db, application_id)
    if a.status not in {"ready_for_review", "in_progress"}: fail("Application must be ready for review.")
    ensure_approved(db, a)
    set_stage(db, a, "in_progress", "Manual portal preparation started; not submitted.")
    db.commit()
    return dict(application=serialize(a), portal=portal_info(a.application_url),
        checklist=["Authenticate manually", "Review verified fields and questions", "Upload approved documents",
                   "Review the complete form", "Click final Submit yourself", "Record employer confirmation"])

@router.post("/applications/{application_id}/record-submission")
def record_submission(application_id: int, payload: Submission, db: Session = Depends(get_db)):
    a = find_application(db, application_id)
    if a.status != "in_progress" or a.date_submitted: fail("Start the approved application before recording submission.")
    if not payload.manually_submitted or not payload.confirmation_reference.strip(): fail("Explicit manual submission confirmation is required.")
    ensure_approved(db, a)
    a.date_submitted = datetime.utcnow()
    a.confirmation_reference = payload.confirmation_reference.strip()
    a.submission_method = "user_recorded_manual"
    set_stage(db, a, "submitted", "User attested submission: " + a.confirmation_reference)
    if payload.follow_up_enabled:
        a.follow_up_date = a.date_submitted + timedelta(days=payload.follow_up_days)
        db.add(FollowUpReminder(application_id=a.id, reminder_type="follow_up", title=f"Follow up: {a.job.company}", due_date=a.follow_up_date))
    event(db, a, "manual_submission_recorded", payload.model_dump())
    db.commit()
    return serialize(a)

@router.put("/applications/{application_id}/status")
def change_status(application_id: int, payload: StageUpdate, db: Session = Depends(get_db)):
    a = find_application(db, application_id)
    if payload.status not in TRANSITIONS.get(a.status, set()): fail("Invalid application stage transition.")
    if payload.status in {"documents_prepared", "ready_for_review", "in_progress"}:
        fail("Use the document preparation, approval or start action for this stage.")
    set_stage(db, a, payload.status, payload.notes)
    if payload.status in {"rejected", "withdrawn", "offer_received"}:
        for r in a.reminders: r.is_dismissed = True
    db.commit()
    return serialize(a)

@router.get("/applications/{application_id}/history")
def history(application_id: int, db: Session = Depends(get_db)):
    find_application(db, application_id)
    return [dict(id=e.id, action=e.action, details=json.loads(e.details), created_at=e.created_at)
        for e in db.query(ApplicationEvent).filter_by(application_id=application_id).order_by(ApplicationEvent.id)]

@router.get("/contacts")
def contacts(db: Session = Depends(get_db)):
    return [{c.name: getattr(row, c.name) for c in row.__table__.columns} for row in db.query(RecruiterContact)]

@router.post("/contacts", status_code=201)
def create_contact(payload: ContactCreate, db: Session = Depends(get_db)):
    if payload.linkedin_url: validate_url_or_fail(payload.linkedin_url)
    row = RecruiterContact(**payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}

@router.get("/applications/{application_id}/outreach")
def outreaches(application_id: int, db: Session = Depends(get_db)):
    a = find_application(db, application_id)
    return [{c.name: getattr(row, c.name) for c in row.__table__.columns} for row in a.recruiter_outreaches]

@router.post("/applications/{application_id}/outreach")
def outreach(application_id: int, payload: OutreachCreate, db: Session = Depends(get_db)):
    a = find_application(db, application_id)
    p = profile_for(db)
    contact = db.get(RecruiterContact, payload.contact_id) if payload.contact_id else None
    if payload.contact_id and not contact: fail("Contact not found.", 404)
    greeting = f"Hello {contact.name}," if contact else "Hello,"
    request = ("Could you consider referring me for this role?" if payload.kind == "referral" else
        "Could you share an update on my application?" if payload.kind == "follow_up" else
        "I would welcome a discussion about the role and its requirements.")
    if payload.kind == "follow_up" and not a.date_submitted: fail("Record a submission before drafting a post-application follow-up.")
    facts = "; ".join(filter(None, [p.current_role, p.current_company]))
    body = f"{greeting}\n\nI am interested in the {a.job.title} position at {a.job.company}. My reviewed profile lists: {facts}. {request}\n\n{p.name}"
    row = RecruiterOutreach(application_id=a.id, contact_id=payload.contact_id, message_type=payload.kind,
        channel=payload.channel, subject=f"{a.job.title} — {a.job.company}", message_body=body)
    db.add(row); event(db, a, "outreach_drafted", payload.model_dump()); db.commit(); db.refresh(row)
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}

@router.put("/outreach/{outreach_id}")
def edit_outreach(outreach_id: int, payload: OutreachEdit, db: Session = Depends(get_db)):
    row = db.get(RecruiterOutreach, outreach_id)
    if not row: fail("Draft not found.", 404)
    if row.is_sent:
        fail("Sent outreach is retained as history. Create a new draft for another message.")
    changed = payload.message_body != row.message_body or payload.subject != row.subject
    if payload.manually_sent and (not row.is_approved or changed): fail("Save and approve this exact message before recording manual sending.")
    row.message_body = payload.message_body; row.subject = payload.subject
    row.is_approved = payload.approved if not changed else False
    row.is_sent = payload.manually_sent
    row.sent_at = datetime.utcnow() if payload.manually_sent else None
    event(db, row.application, "outreach_updated", dict(approved=row.is_approved, manually_sent=row.is_sent, subject=row.subject, message_body=row.message_body, contact_id=row.contact_id, channel=row.channel))
    db.commit()
    return dict(id=row.id, is_approved=row.is_approved, is_sent=row.is_sent)

@router.get("/reminders")
def reminders(db: Session = Depends(get_db)):
    return [{c.name: getattr(row, c.name) for c in row.__table__.columns}
        for row in db.query(FollowUpReminder).order_by(FollowUpReminder.due_date)]

@router.post("/applications/{application_id}/reminders", status_code=201)
def create_reminder(application_id: int, payload: ReminderInput, db: Session = Depends(get_db)):
    a = find_application(db, application_id)
    due = payload.due_date
    if due.tzinfo: due = due.astimezone(timezone.utc).replace(tzinfo=None)
    row = FollowUpReminder(application_id=a.id, title=payload.title, reminder_type=payload.reminder_type, due_date=due)
    db.add(row); event(db, a, "reminder_created", payload.model_dump()); db.commit(); db.refresh(row)
    return dict(id=row.id)

@router.put("/reminders/{reminder_id}")
def update_reminder(reminder_id: int, payload: ReminderUpdate, db: Session = Depends(get_db)):
    from .models import ReminderDelivery
    row = db.get(FollowUpReminder, reminder_id)
    if not row: fail("Reminder not found.", 404)
    if payload.due_date:
        due = payload.due_date
        row.due_date = due.astimezone(timezone.utc).replace(tzinfo=None) if due.tzinfo else due
        db.query(ReminderDelivery).filter_by(reminder_id=row.id).delete()
        if row.reminder_type == "follow_up": row.application.follow_up_date = row.due_date
    row.is_completed = payload.is_completed; row.is_dismissed = payload.is_dismissed
    row.completed_at = datetime.utcnow() if payload.is_completed else None
    event(db, row.application, "reminder_updated", payload.model_dump())
    db.commit()
    return dict(id=row.id)

@router.get("/applications/{application_id}/browser-plan")
def browser_plan(application_id: int, db: Session = Depends(get_db)):
    a = find_application(db, application_id)
    if a.status != "in_progress": fail("Start the approved application first.")
    ensure_approved(db, a)
    prep = json.loads(a.application_questions_json)
    documents = []
    for key in ("cv_document_id", "cover_letter_document_id"):
        d = db.get(GeneratedDocument, prep[key])
        documents.append(dict(kind="cv" if key.startswith("cv") else "cover_letter", filename=d.filename,
            download_path=f"/api/packages/{a.package_id}/download?doc_type={d.doc_type}"))
    return dict(application_id=a.id, url=a.application_url, fields=prep.get("verified_fields", {}),
        questions=prep.get("questions", []), documents=documents, final_submission="manual_only")
