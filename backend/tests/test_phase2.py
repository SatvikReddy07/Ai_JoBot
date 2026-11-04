import os
import json
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from backend.app.models import Job, UserProfile, MasterCV, AIJobAssessment, AIUsageLog
from backend.services.cv_parser import extract_text_from_file, parse_cv_content
from backend.services.gemini_service import (
    analyze_job_with_ai, compute_career_growth_score, compute_job_hash, get_daily_ai_usage
)
from backend.tests.conftest import TestingSessionLocal, client


# 1. PDF Parsing Test
def test_pdf_parsing_pymupdf():
    import fitz  # PyMuPDF
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Raghunath Reddy - Global SHE & Security Manager\ndsm-firmenich, Hyderabad\n18+ years experience in APAC plant safety governance.")
    doc.save(str(tmp_path))
    doc.close()

    try:
        extracted = extract_text_from_file(tmp_path, "sample_cv.pdf")
        assert "Raghunath Reddy" in extracted
        assert "dsm-firmenich" in extracted
        assert "18+ years" in extracted
    finally:
        tmp_path.unlink(missing_ok=True)

# 2. DOCX Parsing Test
def test_docx_parsing_python_docx():
    import docx
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    doc = docx.Document()
    doc.add_heading("Raghunath Reddy", level=0)
    doc.add_paragraph("Global SHE & Security Manager at dsm-firmenich")
    doc.add_paragraph("M.Tech Environmental Engineering, B.Tech Mechanical Engineering, MBA HR, Diploma Industrial Safety")
    doc.save(str(tmp_path))

    try:
        extracted = extract_text_from_file(tmp_path, "sample_cv.docx")
        assert "Raghunath Reddy" in extracted
        assert "Environmental Engineering" in extracted
        assert "Industrial Safety" in extracted
    finally:
        tmp_path.unlink(missing_ok=True)

# 3. Profile Extraction & Merging Test
def test_profile_extraction():
    sample_text = """
    Raghunath Reddy
    Global SHE & Security Manager
    dsm-firmenich, Hyderabad
    Over 18+ years experience leading HSE governance across 19 plants.
    Qualifications: M.Tech Environmental Engineering, B.Tech Mechanical Engineering, MBA Human Resources, Diploma in Industrial Safety.
    Key skills: ISO 14001, ISO 45001, incident investigation, root cause analysis, statutory compliance.
    """
    profile_data = parse_cv_content(sample_text)
    assert profile_data["name"] == "Raghunath Reddy"
    assert profile_data["current_company"] == "dsm-firmenich"
    assert profile_data["experience_years"] == 18
    assert len(profile_data["qualifications"]) >= 4
    assert profile_data["employment_history"] == []  # Unstructured text cannot verify employment history

# 4. Profile API Endpoints & Editable Persistence Test
def test_user_profile_crud_api():
    # 1. Fetch initial profile
    res = client.get("/api/profile")
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Raghunath Reddy"
    assert data["consent_given_for_ai"] is False

    # 2. Update editable fields
    update_payload = {
        "summary": "Updated executive summary highlighting 18+ years global HSE leadership.",
        "experience_years": 19
    }
    res_up = client.put("/api/profile", json=update_payload)
    assert res_up.status_code == 200
    assert res_up.json()["experience_years"] == 19
    assert "Updated executive summary" in res_up.json()["summary"]

    # 3. Toggle AI Consent
    res_consent = client.post("/api/profile/consent", json={"consent_given": True})
    assert res_consent.status_code == 200
    assert res_consent.json()["consent_given_for_ai"] is True

# 5. Career Growth Scoring Test
def test_career_growth_scoring():
    db = TestingSessionLocal()
    job = Job(
        source="greenhouse",
        source_job_id="test_dir_1",
        company="Multinational Chemical Group",
        title="Global Director of HSE & Environmental Governance",
        location="Amsterdam, Netherlands",
        country="Netherlands",
        employment_type="Permanent Full-time",
        is_permanent_fulltime=True,
        description="Oversee multi-site global manufacturing facilities.",
        url="https://boards.greenhouse.io/chem/jobs/test_dir_1"
    )
    db.add(job)
    db.commit()

    profile = db.query(UserProfile).first()
    score, summary = compute_career_growth_score(job, profile)
    assert score >= 80
    assert "Director" in summary or "Global" in summary
    db.close()

# 6. Gemini Integration with Mocks (Success, Caching, and Fallback)
def test_ai_matching_with_mock_and_caching():
    db = TestingSessionLocal()
    job = Job(
        source="greenhouse",
        source_job_id="job_gemini_1",
        company="Global Life Sciences",
        title="Senior Director of EHS & Sustainability",
        location="Berlin, Germany",
        country="Germany",
        employment_type="Permanent Full-time",
        is_permanent_fulltime=True,
        description="Lead global workplace health, safety, and ESG governance across multi-site production facilities. Visa sponsorship available.",
        url="https://boards.greenhouse.io/lifesci/jobs/job_gemini_1"
    )
    db.add(job)
    db.commit()

    profile = db.query(UserProfile).first()
    profile.consent_given_for_ai = True
    db.commit()

    mock_gemini_response = {
        "match_score": 92,
        "application_priority": "High",
        "career_growth_score": 88,
        "career_growth_summary": "Substantial leadership advancement to Senior Director level with European exposure.",
        "matching_skills": ["ISO 14001", "ISO 45001", "Global Governance", "ESG"],
        "missing_requirements": ["German language fluency if local regulatory discussions required"],
        "qualification_alignment": ["M.Tech Environmental Engineering directly aligns"],
        "experience_alignment": ["18+ years multinational leadership matches Director scope"],
        "industry_alignment": ["Strong pharmaceutical and chemical manufacturing fit"],
        "visa_relocation_considerations": "Job explicitly mentions visa sponsorship available for qualified candidates.",
        "reasons_to_apply": ["High executive alignment", "Visa sponsorship offered", "Expansive multi-site responsibility"],
        "reasons_to_reconsider": ["Relocation to Berlin required"],
        "evidence_references": {"quote": "Visa sponsorship available"}
    }

    # Mock Gemini client call
    with patch("backend.services.gemini_service.os.getenv") as mock_env:
        mock_env.side_effect = lambda k, default=None: "mock_api_key_123" if k == "GEMINI_API_KEY" else (default or "")

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = json.dumps(mock_gemini_response)
            mock_model.generate_content.return_value = mock_response
            mock_client.models = mock_model
            mock_client_cls.return_value = mock_client

            # 1. Run AI analysis
            assessment = asyncio.run(analyze_job_with_ai(db, job, profile, force_reanalyze=True))
            assert assessment.match_score == 92
            assert assessment.application_priority == "High"
            assert assessment.engine_used == "ai"

            # 2. Run again without force_reanalyze -> should hit CACHE and NOT call Gemini API again!
            mock_model.generate_content.reset_mock()
            cached_assessment = asyncio.run(analyze_job_with_ai(db, job, profile, force_reanalyze=False))
            assert cached_assessment.id == assessment.id
            mock_model.generate_content.assert_not_called()

    db.close()

# 7. Safe Fallback when API Key is missing or rate limited
def test_ai_matching_fallback_when_no_api_key():
    db = TestingSessionLocal()
    job = Job(
        source="lever",
        source_job_id="job_lever_fall",
        company="Precision Engineering",
        title="Regional Workplace HSE Manager",
        location="Singapore",
        country="Singapore",
        employment_type="Full-time",
        is_permanent_fulltime=True,
        description="Lead APAC regional safety audits and contractor management.",
        url="https://jobs.lever.co/precision/job_lever_fall"
    )
    db.add(job)
    db.commit()

    profile = db.query(UserProfile).first()
    profile.consent_given_for_ai = True
    db.commit()

    # Empty API key
    with patch("backend.services.gemini_service.os.getenv") as mock_env:
        mock_env.return_value = ""

        assessment = asyncio.run(analyze_job_with_ai(db, job, profile, force_reanalyze=True))
        assert assessment.engine_used == "rules_fallback"
        assert assessment.match_score >= 60
        assert "rules engine" in assessment.career_growth_summary.lower()


    db.close()


# 8. AI Usage API Endpoint
def test_ai_usage_endpoint():
    res = client.get("/api/ai/usage")
    assert res.status_code == 200
    data = res.json()
    assert "daily_used" in data
    assert "daily_limit" in data
    assert "remaining" in data

# 9. Master CV Upload Regression Tests (PDF, DOCX, Error handling, and Contract Validation)
def test_upload_master_cv_pdf():
    import fitz
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Raghunath Reddy\nGlobal SHE & Security Manager\ndsm-firmenich, Hyderabad\n18+ years experience in APAC plant safety governance.")
    doc.save(str(tmp_path))
    doc.close()

    try:
        with open(tmp_path, "rb") as f:
            res = client.post(
                "/api/profile/upload-cv",
                files={"file": ("master_cv_test.pdf", f, "application/pdf")}
            )
        assert res.status_code == 200
        data = res.json()
        # Verify exact contract expected by frontend
        assert "message" in data
        assert "cv_id" in data
        assert "filename" in data
        assert data["filename"] == "master_cv_test.pdf"
        assert "profile" in data
        prof = data["profile"]
        assert prof["name"] == "Raghunath Reddy"
        assert prof["current_company"] == "dsm-firmenich"
        assert isinstance(prof["employment_history"], list)
        assert isinstance(prof["qualifications"], list)
        assert isinstance(prof["skills"], list)
        assert len(prof["employment_history"]) > 0
    finally:
        tmp_path.unlink(missing_ok=True)

def test_upload_master_cv_docx():
    import docx
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    doc = docx.Document()
    doc.add_heading("Raghunath Reddy", level=0)
    doc.add_paragraph("Global SHE & Security Manager at dsm-firmenich")
    doc.add_paragraph("18+ years experience in multi-site plant safety governance.")
    doc.save(str(tmp_path))

    try:
        with open(tmp_path, "rb") as f:
            res = client.post(
                "/api/profile/upload-cv",
                files={"file": ("master_cv_test.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            )
        assert res.status_code == 200
        data = res.json()
        assert "profile" in data
        prof = data["profile"]
        assert prof["name"] == "Raghunath Reddy"
        assert prof["current_company"] == "dsm-firmenich"
        assert isinstance(prof["employment_history"], list)
    finally:
        tmp_path.unlink(missing_ok=True)

def test_upload_master_cv_invalid_file_type():
    res = client.post(
        "/api/profile/upload-cv",
        files={"file": ("invalid_resume.txt", b"This is a plain text file", "text/plain")}
    )
    assert res.status_code == 400
    assert "Invalid file type" in res.json()["detail"]

def test_upload_master_cv_empty_file():
    res = client.post(
        "/api/profile/upload-cv",
        files={"file": ("empty_resume.pdf", b"", "application/pdf")}
    )
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()

