import os
import json
import zipfile
import tempfile
from pathlib import Path
import pytest
import docx
import fitz

from backend.app.models import Job, UserProfile, ApplicationPackage, GeneratedDocument
from backend.app.schemas import TailoredCVContent, TailoredCoverLetterContent
from backend.services.ats_service import analyze_ats_keywords
from backend.services.tailoring_service import (
    generate_tailored_cv_rules, generate_tailored_cover_letter_rules, TEMPLATE_CONFIGS
)
from backend.services.cv_generator import (
    generate_cv_docx, generate_cv_pdf, generate_cover_letter_docx, generate_cover_letter_pdf,
    check_pdf_converter_availability
)
from backend.services.package_service import (
    create_application_package, update_document_content, approve_package, PACKAGES_DIR
)
from backend.services.notification_service import check_and_notify_high_match_job
from backend.tests.conftest import TestingSessionLocal, client

@pytest.fixture
def sample_job(db_session):
    job = Job(
        source="greenhouse",
        source_job_id="p3_test_job_001",
        company="Multinational Nutrition Corp",
        title="Global Workplace HSE Manager",
        location="Singapore",
        country="Singapore",
        employment_type="Full-time",
        is_permanent_fulltime=True,
        description=(
            "We are seeking a Global Workplace HSE Manager to lead our multi-site manufacturing safety governance. "
            "Key responsibilities include ISO 14001 and ISO 45001 compliance, contractor safety management, "
            "incident investigation using Root Cause Analysis (RCA), and APAC regional HSE performance metrics. "
            "Requires 15+ years experience and an environmental engineering degree."
        ),
        url="https://boards.greenhouse.io/multinational/jobs/p3_test_job_001",
        match_score=90,
        match_level="Excellent Match"
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job

@pytest.fixture
def candidate_profile(db_session):
    profile = db_session.query(UserProfile).first()
    return {
        "name": profile.name,
        "current_role": profile.current_role,
        "current_company": profile.current_company,
        "location": profile.location,
        "experience_years": profile.experience_years,
        "summary": profile.summary,
        "employment_history": json.loads(profile.employment_history),
        "qualifications": json.loads(profile.qualifications),
        "skills": json.loads(profile.skills),
        "certifications": json.loads(profile.certifications),
        "achievements": json.loads(profile.achievements)
    }

# 1. ATS Keyword Analysis Test
def test_ats_keyword_analysis(sample_job, candidate_profile):
    res = analyze_ats_keywords(sample_job.title, sample_job.description, candidate_profile)
    assert res["overall_coverage_pct"] >= 50.0
    matched_words = [m["keyword"].lower() for m in res["matched_keywords"]]
    assert any("iso 14001" in w for w in matched_words)
    assert any("root cause analysis" in w or "incident investigation" in w for w in matched_words)
    assert len(res["legitimate_suggestions"]) > 0
    assert "guarantee" in res["disclaimer"].lower()

# 2. Tailored CV Content (Rules Fallback & Templates)
def test_tailored_cv_generation(sample_job, candidate_profile):
    for tmpl in ["global_regional_hse", "manufacturing_industrial_ehs", "corporate_workplace_hse"]:
        cv = generate_tailored_cv_rules(
            profile=candidate_profile,
            job_company=sample_job.company,
            job_title=sample_job.title,
            job_desc=sample_job.description,
            template_name=tmpl
        )
        assert cv.name == "Raghunath Reddy"
        assert sample_job.company in cv.summary
        assert sample_job.title in cv.headline or sample_job.title in cv.summary
        assert len(cv.core_competencies) > 0
        assert len(cv.employment_history) >= 4
        assert cv.generation_method == "rules_fallback"

# 3. Tailored Cover Letter Content
def test_tailored_cover_letter_generation(sample_job, candidate_profile):
    cl = generate_tailored_cover_letter_rules(
        profile=candidate_profile,
        job_company=sample_job.company,
        job_title=sample_job.title,
        job_location=sample_job.location
    )
    assert cl.candidate_name == "Raghunath Reddy"
    assert sample_job.company in cl.company_name
    assert sample_job.title in cl.job_title
    assert len(cl.body_paragraphs) == 3
    # Word count check: between 200 and 400 words
    total_words = sum(len(p.split()) for p in cl.body_paragraphs)
    assert 180 <= total_words <= 420

# 4. DOCX Document Generation Validity
def test_cv_and_cl_docx_generation(sample_job, candidate_profile, tmp_path):
    cv = generate_tailored_cv_rules(candidate_profile, sample_job.company, sample_job.title, sample_job.description)
    cv_path = tmp_path / "test_cv.docx"
    generate_cv_docx(cv, cv_path)
    assert cv_path.exists()
    assert cv_path.stat().st_size > 1000

    # Verify DOCX can be opened and parsed
    doc = docx.Document(str(cv_path))
    full_text = "\n".join([p.text for p in doc.paragraphs])
    assert "Raghunath Reddy" in full_text
    assert "EXECUTIVE PROFESSIONAL SUMMARY" in full_text
    assert "dsm-firmenich" in full_text

    cl = generate_tailored_cover_letter_rules(candidate_profile, sample_job.company, sample_job.title, sample_job.location)
    cl_path = tmp_path / "test_cl.docx"
    generate_cover_letter_docx(cl, cl_path)
    assert cl_path.exists()
    doc_cl = docx.Document(str(cl_path))
    cl_text = "\n".join([p.text for p in doc_cl.paragraphs])
    assert sample_job.company in cl_text

# 5. PDF Generation & Selectable Text Layer
def test_cv_and_cl_pdf_generation(sample_job, candidate_profile, tmp_path):
    cv = generate_tailored_cv_rules(candidate_profile, sample_job.company, sample_job.title, sample_job.description)
    cv_pdf_path = tmp_path / "test_cv.pdf"
    generate_cv_pdf(cv, cv_pdf_path)
    assert cv_pdf_path.exists()
    assert cv_pdf_path.stat().st_size > 1000

    # Verify PDF using PyMuPDF (fitz)
    pdf = fitz.open(str(cv_pdf_path))
    assert len(pdf) >= 1
    pdf_text = "\n".join([page.get_text() for page in pdf])
    pdf.close()
    assert "Raghunath Reddy" in pdf_text
    assert "Environmental Engineering" in pdf_text

# 6. Complete Application Package & ZIP Creation
def test_application_package_creation_workflow(db_session, sample_job, candidate_profile):
    pkg = create_application_package(
        db=db_session,
        job=sample_job,
        profile_dict=candidate_profile,
        template_name="global_regional_hse",
        custom_notes="Targeting Singapore APAC vacancy"
    )
    assert pkg.id is not None
    assert pkg.status == "draft"
    assert Path(pkg.package_dir).exists()
    assert Path(pkg.zip_path).exists()

    # Verify documents in package
    doc_types = [d.doc_type for d in pkg.documents]
    assert "cv_docx" in doc_types
    assert "cv_pdf" in doc_types
    assert "cover_letter_docx" in doc_types
    assert "cover_letter_pdf" in doc_types
    assert "job_description" in doc_types
    assert "checklist" in doc_types
    assert "metadata" in doc_types

    # Verify ZIP contains all files
    with zipfile.ZipFile(pkg.zip_path, "r") as zf:
        namelist = zf.namelist()
        assert any(n.endswith(".docx") for n in namelist)
        assert any(n.endswith(".pdf") for n in namelist)
        assert any("Checklist" in n for n in namelist)

# 7. Document Revision & Versioning
def test_document_revision_and_approval(db_session, sample_job, candidate_profile):
    pkg = create_application_package(db=db_session, job=sample_job, profile_dict=candidate_profile)
    cl_doc = [d for d in pkg.documents if d.doc_type == "cover_letter_docx"][0]

    orig_content = json.loads(cl_doc.content_text)
    orig_content["body_paragraphs"][0] = "Updated tailored opening statement emphasizing 18+ years HSE leadership."
    new_json = json.dumps(orig_content)

    updated_doc = update_document_content(
        db=db_session,
        package=pkg,
        document=cl_doc,
        new_content_text=new_json,
        change_summary="Refined opening statement"
    )
    assert updated_doc.version_number == 2
    assert len(updated_doc.versions) == 1
    assert updated_doc.versions[0].version_number == 1

    # Approve package
    approved_pkg = approve_package(db=db_session, package=pkg, approved_by="Raghunath Reddy")
    assert approved_pkg.status == "approved"
    assert len(approved_pkg.approvals) >= 1

# 8. API Integration Endpoints
def test_phase3_api_endpoints():
    db = TestingSessionLocal()
    job = Job(
        source="greenhouse",
        source_job_id="p3_api_job_002",
        company="Multinational Nutrition Corp",
        title="Global Workplace HSE Manager",
        location="Singapore",
        country="Singapore",
        employment_type="Full-time",
        is_permanent_fulltime=True,
        description="We are seeking a Global Workplace HSE Manager to lead our multi-site safety governance with ISO 14001.",
        url="https://boards.greenhouse.io/multi/jobs/p3_api_job_002",
        match_score=90
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = job.id
    db.close()

    # 1. ATS Analysis endpoint
    r1 = client.get(f"/api/jobs/{job_id}/ats-analysis")
    assert r1.status_code == 200
    assert "overall_coverage_pct" in r1.json()

    # 2. Generate CV preview endpoint
    r2 = client.post(f"/api/jobs/{job_id}/generate-cv?template_name=global_regional_hse")
    assert r2.status_code == 200
    assert r2.json()["name"] == "Raghunath Reddy"

    # 3. Generate Cover letter preview endpoint
    r3 = client.post(f"/api/jobs/{job_id}/generate-cover-letter?template_name=global_regional_hse")
    assert r3.status_code == 200
    assert len(r3.json()["body_paragraphs"]) == 3

    # 4. Generate Package endpoint
    r4 = client.post(
        f"/api/jobs/{job_id}/generate-package",
        json={"template_name": "manufacturing_industrial_ehs", "custom_notes": "API test package"}
    )
    assert r4.status_code == 200
    pkg_data = r4.json()
    assert pkg_data["status"] == "draft"
    assert len(pkg_data["documents"]) >= 6
    pkg_id = pkg_data["id"]

    # 5. Get Package endpoint
    r5 = client.get(f"/api/packages/{pkg_id}")
    assert r5.status_code == 200
    assert r5.json()["id"] == pkg_id

    # 6. Approve Package endpoint
    r6 = client.post(f"/api/packages/{pkg_id}/approve", json={"approved_by": "Raghunath Reddy"})
    assert r6.status_code == 200
    assert r6.json()["status"] == "approved"

    # 7. Download ZIP endpoint
    r7 = client.get(f"/api/packages/{pkg_id}/download")
    assert r7.status_code == 200
    assert r7.headers["content-type"] == "application/zip"

    # 8. PDF Converter Status endpoint
    r8 = client.get("/api/pdf-converter/status")
    assert r8.status_code == 200
    assert r8.json()["available"] is True

# 9. High-Match Desktop Notification Logic
def test_high_match_notification(db_session, sample_job):
    sample_job.match_score = 92
    db_session.commit()
    # Test dispatch without quiet hours
    log = check_and_notify_high_match_job(db_session, sample_job, min_score=85, respect_quiet=False)
    assert log is not None
    assert log.job_id == sample_job.id
    assert log.match_score == 92

    # Second call should be suppressed as duplicate
    duplicate_log = check_and_notify_high_match_job(db_session, sample_job, min_score=85, respect_quiet=False)
    assert duplicate_log is None
