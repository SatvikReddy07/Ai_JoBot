import json
import logging
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session

from backend.app.database import BASE_DIR, DATA_DIR
from backend.app.models import (
    Job, UserProfile, ApplicationPackage, GeneratedDocument, 
    DocumentVersion, DocumentApproval, GenerationAuditLog
)
from backend.app.schemas import (
    TailoredCVContent, TailoredCoverLetterContent, PackageGenerateRequest
)
from backend.services.tailoring_service import generate_tailored_cv, generate_tailored_cover_letter
from backend.services.cv_generator import (
    generate_cv_docx, generate_cv_pdf, generate_cover_letter_docx, generate_cover_letter_pdf
)
from backend.services.ats_service import analyze_ats_keywords

logger = logging.getLogger(__name__)

PACKAGES_DIR = DATA_DIR / "packages"
PACKAGES_DIR.mkdir(parents=True, exist_ok=True)

def sanitize_filename(text: str) -> str:
    """Safe ASCII filename sanitizer preventing path traversal."""
    cleaned = re.sub(r'[\\/*?:"<>|]', "", text)
    cleaned = re.sub(r'\s+', "_", cleaned)
    return cleaned.strip("._")[:60]

def create_application_package(
    db: Session,
    job: Job,
    profile_dict: Dict[str, Any],
    template_name: str = "global_regional_hse",
    custom_notes: Optional[str] = None,
    consent_given: bool = False,
    force_override: bool = False
) -> ApplicationPackage:
    """
    Assembles a complete, job-specific tailored application package:
    - Tailored CV (.docx & .pdf)
    - Executive Cover Letter (.docx & .pdf)
    - Job Description (.txt)
    - Application Checklist (.txt)
    - Package Metadata (.json)
    - Downloadable ZIP archive
    """
    # 0. Occupational Relevance & Low Match Warning Gate
    if (job.match_score < 50 or "Excluded - Unrelated" in (job.match_level or "")) and not force_override:
        raise ValueError(
            f"Occupational Relevance Warning: Position '{job.title}' at {job.company} is classified as {job.match_level} "
            f"({job.match_score}/100) and appears unrelated to HSE executive leadership. "
            f"Generating an HSE application package for an unrelated role requires explicit confirmation (force_override=True)."
        )

    # 1. Run ATS Keyword Analysis
    ats_data = analyze_ats_keywords(job.title, job.description, profile_dict)
    ats_score = ats_data.get("overall_coverage_pct", 0.0)

    # 2. Create ApplicationPackage DB record
    timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    package = ApplicationPackage(
        job_id=job.id,
        template_name=template_name,
        status="draft",
        package_dir="",
        ats_match_score=ats_score,
        ats_analysis_json=json.dumps(ats_data),
        notes=custom_notes,
        generation_method="rules_fallback",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(package)
    db.commit()
    db.refresh(package)

    # 3. Create unique local folder
    pkg_dir = PACKAGES_DIR / f"pkg_{package.id}_{sanitize_filename(job.company)}_{timestamp_str}"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    package.package_dir = str(pkg_dir)

    # 4. Generate local content directly; avoid nested event loops in API workers.
    from backend.services.tailoring_service import generate_tailored_cv_rules, generate_tailored_cover_letter_rules
    cv_data = generate_tailored_cv_rules(profile_dict, job.company, job.title, job.description, template_name)
    cl_data = generate_tailored_cover_letter_rules(profile_dict, job.company, job.title, job.location, template_name)

    package.generation_method = cv_data.generation_method

    safe_candidate = sanitize_filename(profile_dict.get("name", "Raghunath_Reddy"))
    safe_title = sanitize_filename(job.title)

    # 5. Generate Documents
    # A. CV DOCX
    cv_docx_name = f"CV_{safe_candidate}_{safe_title}.docx"
    cv_docx_path = pkg_dir / cv_docx_name
    generate_cv_docx(cv_data, cv_docx_path)
    doc_cv_docx = GeneratedDocument(
        package_id=package.id,
        doc_type="cv_docx",
        filename=cv_docx_name,
        file_path=str(cv_docx_path),
        content_text=json.dumps(cv_data.dict()),
        version_number=1,
        is_approved=False
    )
    db.add(doc_cv_docx)

    # B. CV PDF
    cv_pdf_name = f"CV_{safe_candidate}_{safe_title}.pdf"
    cv_pdf_path = pkg_dir / cv_pdf_name
    generate_cv_pdf(cv_data, cv_pdf_path)
    doc_cv_pdf = GeneratedDocument(
        package_id=package.id,
        doc_type="cv_pdf",
        filename=cv_pdf_name,
        file_path=str(cv_pdf_path),
        content_text=None,
        version_number=1,
        is_approved=False
    )
    db.add(doc_cv_pdf)

    # C. Cover Letter DOCX
    cl_docx_name = f"Cover_Letter_{safe_candidate}_{safe_title}.docx"
    cl_docx_path = pkg_dir / cl_docx_name
    generate_cover_letter_docx(cl_data, cl_docx_path)
    doc_cl_docx = GeneratedDocument(
        package_id=package.id,
        doc_type="cover_letter_docx",
        filename=cl_docx_name,
        file_path=str(cl_docx_path),
        content_text=json.dumps(cl_data.dict()),
        version_number=1,
        is_approved=False
    )
    db.add(doc_cl_docx)

    # D. Cover Letter PDF
    cl_pdf_name = f"Cover_Letter_{safe_candidate}_{safe_title}.pdf"
    cl_pdf_path = pkg_dir / cl_pdf_name
    generate_cover_letter_pdf(cl_data, cl_pdf_path)
    doc_cl_pdf = GeneratedDocument(
        package_id=package.id,
        doc_type="cover_letter_pdf",
        filename=cl_pdf_name,
        file_path=str(cl_pdf_path),
        content_text=None,
        version_number=1,
        is_approved=False
    )
    db.add(doc_cl_pdf)

    # E. Job Description text
    jd_txt_name = f"Job_Description_{sanitize_filename(job.company)}_{safe_title}.txt"
    jd_txt_path = pkg_dir / jd_txt_name
    jd_content = (
        f"COMPANY: {job.company}\n"
        f"POSITION: {job.title}\n"
        f"LOCATION: {job.location}\n"
        f"URL: {job.url}\n"
        f"DISCOVERED AT: {job.discovered_at}\n\n"
        f"--- JOB VACANCY DESCRIPTION ---\n\n"
        f"{job.description}\n"
    )
    with open(jd_txt_path, "w", encoding="utf-8") as f:
        f.write(jd_content)
    doc_jd = GeneratedDocument(
        package_id=package.id,
        doc_type="job_description",
        filename=jd_txt_name,
        file_path=str(jd_txt_path),
        content_text=jd_content,
        version_number=1,
        is_approved=True
    )
    db.add(doc_jd)

    # F. Application Checklist text
    chk_name = f"Application_Checklist_{safe_title}.txt"
    chk_path = pkg_dir / chk_name
    chk_content = (
        f"HSE CAREER AGENT — EXECUTIVE APPLICATION CHECKLIST\n"
        f"Target Opportunity: {job.title} at {job.company}\n"
        f"Package ID: {package.id} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"[ ] 1. REVIEW TAILORED CV (DOCX/PDF):\n"
        f"    • Confirm APAC 19-plant reporting and ISO 14001/45001 highlights are clear.\n"
        f"    • Verify engineering degrees (M.Tech Environmental, B.Tech Mech) and certifications.\n"
        f"[ ] 2. CUSTOMIZE COVER LETTER:\n"
        f"    • Ensure specific alignment with {job.company}'s site or regional scope.\n"
        f"[ ] 3. LOCATION & VISA CHECK:\n"
        f"    • Role Location: {job.location}\n"
        f"    • Sponsorship Status: {job.sponsorship_status}\n"
        f"[ ] 4. FINAL APPROVAL:\n"
        f"    • Approve package in Application Studio before submission.\n"
        f"[ ] 5. OFFICIAL PORTAL SUBMISSION:\n"
        f"    • Submit exclusively via official portal: {job.url}\n"
        f"    • Update application status to 'Applied' in HSE Career Agent dashboard.\n"
    )
    with open(chk_path, "w", encoding="utf-8") as f:
        f.write(chk_content)
    doc_chk = GeneratedDocument(
        package_id=package.id,
        doc_type="checklist",
        filename=chk_name,
        file_path=str(chk_path),
        content_text=chk_content,
        version_number=1,
        is_approved=True
    )
    db.add(doc_chk)

    # G. Package Metadata JSON
    meta_name = "Package_Metadata.json"
    meta_path = pkg_dir / meta_name
    meta_content = {
        "package_id": package.id,
        "job_id": job.id,
        "employer": job.company,
        "position_title": job.title,
        "application_url": job.url,
        "generation_date": datetime.utcnow().isoformat(),
        "template_used": template_name,
        "generation_method": package.generation_method,
        "career_suitability_score": job.match_score,
        "ats_keyword_coverage_pct": ats_score,
        "ats_match_score": ats_score,
        "status": "draft",
        "disclaimer": "Career suitability score (career alignment) and ATS keyword coverage (evidence alignment) are independent metrics. Neither represents an interview probability or hiring guarantee.",
        "documents": [
            cv_docx_name, cv_pdf_name, cl_docx_name, cl_pdf_name, jd_txt_name, chk_name
        ]
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta_content, f, indent=2)
    doc_meta = GeneratedDocument(
        package_id=package.id,
        doc_type="metadata",
        filename=meta_name,
        file_path=str(meta_path),
        content_text=json.dumps(meta_content),
        version_number=1,
        is_approved=True
    )
    db.add(doc_meta)

    # 6. Bundle ZIP Package
    zip_filename = f"Application_Package_{sanitize_filename(job.company)}_{safe_title}.zip"
    zip_path = pkg_dir / zip_filename
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(cv_docx_path, arcname=cv_docx_name)
        zf.write(cv_pdf_path, arcname=cv_pdf_name)
        zf.write(cl_docx_path, arcname=cl_docx_name)
        zf.write(cl_pdf_path, arcname=cl_pdf_name)
        zf.write(jd_txt_path, arcname=jd_txt_name)
        zf.write(chk_path, arcname=chk_name)
        zf.write(meta_path, arcname=meta_name)

    package.zip_path = str(zip_path)

    # 7. Audit Log
    audit = GenerationAuditLog(
        package_id=package.id,
        action="create_package",
        details=f"Package generated with template '{template_name}' for {job.company} - {job.title}",
        engine_used=package.generation_method,
        timestamp=datetime.utcnow()
    )
    db.add(audit)

    db.commit()
    db.refresh(package)
    return package

def update_document_content(
    db: Session,
    package: ApplicationPackage,
    document: GeneratedDocument,
    new_content_text: str,
    change_summary: str = "Manual user revision"
) -> GeneratedDocument:
    """
    Safely edits a document draft.
    Preserves version history.
    Requires reapproval if package was previously approved.
    """
    # 1. Save prior version to DocumentVersion table
    prior_version = DocumentVersion(
        document_id=document.id,
        version_number=document.version_number,
        content_text=document.content_text or "",
        file_path=document.file_path,
        change_summary=change_summary,
        created_at=datetime.utcnow()
    )
    db.add(prior_version)

    # 2. Update document
    document.version_number += 1
    document.content_text = new_content_text
    document.is_approved = False
    document.updated_at = datetime.utcnow()

    # 3. Substantive edit requires package reapproval
    if package.status == "approved":
        package.status = "in_review"
    package.updated_at = datetime.utcnow()

    # 4. Rebuild physical files
    pkg_dir = Path(package.package_dir)
    if document.doc_type == "cv_docx":
        try:
            cv_dict = json.loads(new_content_text)
            cv_content = TailoredCVContent(**cv_dict)
            generate_cv_docx(cv_content, Path(document.file_path))
            
            # Also regenerate matching PDF if exists
            pdf_doc = db.query(GeneratedDocument).filter(
                GeneratedDocument.package_id == package.id,
                GeneratedDocument.doc_type == "cv_pdf"
            ).first()
            if pdf_doc:
                generate_cv_pdf(cv_content, Path(pdf_doc.file_path))
                pdf_doc.version_number = document.version_number
                pdf_doc.is_approved = False
        except Exception as exc:
            logger.error(f"Failed to rebuild CV files on update: {exc}")

    elif document.doc_type == "cover_letter_docx":
        try:
            cl_dict = json.loads(new_content_text)
            cl_content = TailoredCoverLetterContent(**cl_dict)
            generate_cover_letter_docx(cl_content, Path(document.file_path))

            # Also regenerate matching PDF
            pdf_doc = db.query(GeneratedDocument).filter(
                GeneratedDocument.package_id == package.id,
                GeneratedDocument.doc_type == "cover_letter_pdf"
            ).first()
            if pdf_doc:
                generate_cover_letter_pdf(cl_content, Path(pdf_doc.file_path))
                pdf_doc.version_number = document.version_number
                pdf_doc.is_approved = False
        except Exception as exc:
            logger.error(f"Failed to rebuild Cover Letter files on update: {exc}")

    # 5. Rebuild ZIP archive
    if package.zip_path and Path(package.zip_path).exists():
        try:
            with zipfile.ZipFile(package.zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for doc in package.documents:
                    p = Path(doc.file_path)
                    if p.exists() and p != Path(package.zip_path):
                        zf.write(p, arcname=doc.filename)
        except Exception as exc:
            logger.warning(f"Could not re-zip package: {exc}")

    # Audit log
    audit = GenerationAuditLog(
        package_id=package.id,
        action="update_document",
        details=f"Document {document.filename} updated to version {document.version_number}: {change_summary}",
        engine_used="user_edit",
        timestamp=datetime.utcnow()
    )
    db.add(audit)

    db.commit()
    db.refresh(document)
    return document

def approve_package(
    db: Session,
    package: ApplicationPackage,
    approved_by: str = "Raghunath Reddy",
    notes: Optional[str] = None
) -> ApplicationPackage:
    """
    Approves the tailored package. Marks documents approved and records formal approval.
    """
    package.status = "approved"
    package.updated_at = datetime.utcnow()

    for doc in package.documents:
        doc.is_approved = True

    approval = DocumentApproval(
        package_id=package.id,
        approved_by=approved_by,
        version_approved=1,
        approval_notes=notes or "Candidate approved final tailored documents",
        approved_at=datetime.utcnow()
    )
    db.add(approval)

    audit = GenerationAuditLog(
        package_id=package.id,
        action="approve",
        details=f"Package approved by {approved_by}",
        engine_used="user_approval",
        timestamp=datetime.utcnow()
    )
    db.add(audit)

    db.commit()
    db.refresh(package)
    return package

def format_package_response(package: ApplicationPackage) -> Dict[str, Any]:
    """Helper to format ApplicationPackage for API response."""
    job = package.job
    ats_dict = json.loads(package.ats_analysis_json or "{}")

    docs = []
    for d in package.documents:
        versions = [
            {
                "id": v.id,
                "document_id": v.document_id,
                "version_number": v.version_number,
                "change_summary": v.change_summary,
                "created_at": v.created_at
            }
            for v in d.versions
        ]
        docs.append({
            "id": d.id,
            "package_id": d.package_id,
            "doc_type": d.doc_type,
            "filename": d.filename,
            "file_path": d.file_path,
            "content_text": d.content_text,
            "version_number": d.version_number,
            "is_approved": d.is_approved,
            "created_at": d.created_at,
            "updated_at": d.updated_at,
            "versions": versions
        })

    approvals = [
        {
            "id": a.id,
            "package_id": a.package_id,
            "approved_by": a.approved_by,
            "version_approved": a.version_approved,
            "approval_notes": a.approval_notes,
            "approved_at": a.approved_at
        }
        for a in package.approvals
    ]

    has_zip = bool(package.zip_path and Path(package.zip_path).exists())

    return {
        "id": package.id,
        "job_id": package.job_id,
        "job_title": job.title if job else "Unknown Role",
        "company": job.company if job else "Unknown Company",
        "job_location": job.location if job else "",
        "template_name": package.template_name,
        "status": package.status,
        "generation_method": package.generation_method,
        "ats_match_score": package.ats_match_score,
        "ats_analysis": ats_dict,
        "notes": package.notes,
        "has_zip": has_zip,
        "created_at": package.created_at,
        "updated_at": package.updated_at,
        "documents": docs,
        "approvals": approvals
    }
