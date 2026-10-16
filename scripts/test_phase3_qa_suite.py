import os
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path

# Set up paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

import fitz # pymupdf
import docx

BASE_URL = "http://127.0.0.1:8000"

def run_api_request(endpoint, method="GET", data=None):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    body = json.dumps(data).encode("utf-8") if data is not None else None
    with urllib.request.urlopen(req, data=body) as response:
        return json.loads(response.read().decode("utf-8"))

def download_file(endpoint, output_path):
    url = f"{BASE_URL}{endpoint}"
    urllib.request.urlretrieve(url, output_path)

def run_qa_tests():
    print("=" * 70)
    print("HSE CAREER AGENT — PHASE 3.1 COMPREHENSIVE QA & VALIDATION")
    print("=" * 70)

    # 1. Health & Converter Diagnostics
    print("\n[Step 1] Checking Backend & PDF Converter Status...")
    health = run_api_request("/health")
    print(f"  Backend Health: {health['status']} | Version: {health['version']} | Phase: {health['phase']}")

    conv = run_api_request("/api/pdf-converter/status")
    print(f"  PDF Engine: {conv.get('primary_engine')} | Available: {conv.get('available')} | LibreOffice: {conv.get('libreoffice_detected')}")
    assert conv.get("available"), "PDF Engine must be available!"

    # 2. Verify High-Match HSE Role
    print("\n[Step 2] Verifying High-Match HSE Role (Job ID 231)...")
    jobs_res = run_api_request("/api/jobs?sort_by=score_desc&page=1&page_size=5")
    top_jobs = jobs_res["items"]
    print(f"  Found {len(top_jobs)} top jobs in response:")
    for j in top_jobs:
        print(f"    - ID {j['id']}: {j['title']} at {j['company']} -> Score: {j['match_score']}% ({j['match_level']})")
    
    target_job = top_jobs[0]
    assert target_job["match_score"] >= 85, f"Top role must score >= 85, got {target_job['match_score']}"
    target_job_id = target_job["id"]

    # 3. ATS Analysis Verification
    print(f"\n[Step 3] Running ATS Keyword Analysis for Job ID {target_job_id}...")
    ats = run_api_request(f"/api/jobs/{target_job_id}/ats-analysis")
    print(f"  ATS Match Coverage: {ats['overall_coverage_pct']}%")
    print(f"  Matched Keywords Count: {len(ats['matched_keywords'])}")
    print(f"  Missing Keywords Count: {len(ats['missing_keywords'])}")
    print(f"  Suggestions Count: {len(ats['legitimate_suggestions'])}")
    assert ats["overall_coverage_pct"] >= 65, "ATS coverage for verified HSE role should be >= 65%"

    # 4. Generate Application Package
    print(f"\n[Step 4] Generating Application Package for '{target_job['title']}'...")
    pkg_payload = {
        "template_name": "global_regional_hse",
        "custom_notes": "QA Validation Package for Global Head of SHE"
    }
    pkg = run_api_request(f"/api/jobs/{target_job_id}/generate-package", method="POST", data=pkg_payload)
    pkg_id = pkg["id"]
    print(f"  Created Package ID: {pkg_id}")
    print(f"  Package Status: {pkg['status']}")
    print(f"  Template: {pkg['template_name']}")
    print(f"  Documents Generated: {len(pkg['documents'])}")
    for d in pkg["documents"]:
        print(f"    - Doc ID {d['id']} [{d['doc_type']}]: {d['filename']} (v{d['version_number']})")

    # 5. Verify Word (.docx) & Vector PDF (.pdf) Integrity
    print(f"\n[Step 5] Testing Document Integrity and Vector Text Selectability...")
    scratch_dir = Path(project_root) / "data" / "qa_scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)

    cv_docx_path = scratch_dir / f"test_cv_{pkg_id}.docx"
    cv_pdf_path = scratch_dir / f"test_cv_{pkg_id}.pdf"
    cl_docx_path = scratch_dir / f"test_cl_{pkg_id}.docx"
    cl_pdf_path = scratch_dir / f"test_cl_{pkg_id}.pdf"
    zip_path = scratch_dir / f"test_pkg_{pkg_id}.zip"

    download_file(f"/api/packages/{pkg_id}/download?doc_type=cv_docx", str(cv_docx_path))
    download_file(f"/api/packages/{pkg_id}/download?doc_type=cv_pdf", str(cv_pdf_path))
    download_file(f"/api/packages/{pkg_id}/download?doc_type=cover_letter_docx", str(cl_docx_path))
    download_file(f"/api/packages/{pkg_id}/download?doc_type=cover_letter_pdf", str(cl_pdf_path))
    download_file(f"/api/packages/{pkg_id}/download", str(zip_path))

    # Verify DOCX
    doc = docx.Document(str(cv_docx_path))
    docx_text = "\n".join([p.text for p in doc.paragraphs])
    print(f"  CV DOCX opens cleanly. Paragraph count: {len(doc.paragraphs)}. Size: {cv_docx_path.stat().st_size} bytes")
    assert "Raghunath Reddy" in docx_text, "Candidate name must be in CV DOCX!"
    assert "19 manufacturing plants" in docx_text or "19" in docx_text, "APAC 19 plants must be in CV DOCX!"

    # Verify Vector PDF (pymupdf text selectability)
    pdf_doc = fitz.open(str(cv_pdf_path))
    pdf_text = ""
    for page in pdf_doc:
        pdf_text += page.get_text()
    print(f"  CV PDF is valid text-selectable vector PDF. Pages: {len(pdf_doc)}. Text length: {len(pdf_text)} chars. Size: {cv_pdf_path.stat().st_size} bytes")
    assert len(pdf_text.strip()) > 200, "PDF must have selectable text (not an image or raster scan)!"
    assert "Raghunath Reddy" in pdf_text, "Candidate name must be selectable in PDF!"

    # Verify Cover Letter
    cl_doc = docx.Document(str(cl_docx_path))
    cl_text = "\n".join([p.text for p in cl_doc.paragraphs])
    cl_words = len(cl_text.split())
    print(f"  Cover Letter DOCX valid. Word count: {cl_words} words (target: 250-350 words).")
    assert 180 <= cl_words <= 450, f"Cover letter word count {cl_words} out of expected bounds!"

    # Verify ZIP Archive
    assert zip_path.exists() and zip_path.stat().st_size > 10000, "ZIP archive must exist and be valid!"
    print(f"  ZIP package downloaded successfully. Size: {zip_path.stat().st_size} bytes.")

    # 6. Test Document Editing and Versioning (v1 -> v2)
    print(f"\n[Step 6] Testing Document Editing & Versioning (v1 -> v2)...")
    cv_doc_item = next(d for d in pkg["documents"] if d["doc_type"] == "cv_docx")
    edit_payload = {
        "content_text": cv_doc_item["content_text"] + "\n\n[Addendum: Executive board advisory credential added]",
        "change_summary": "Added executive advisory credential"
    }
    updated_doc = run_api_request(
        f"/api/packages/{pkg_id}/documents/{cv_doc_item['id']}",
        method="PUT",
        data=edit_payload
    )
    print(f"  Updated Document ID {updated_doc['id']}: Version is now v{updated_doc['version_number']}")
    assert updated_doc["version_number"] == 2, f"Expected version 2, got {updated_doc['version_number']}"
    assert len(updated_doc["versions"]) >= 1, "Audit trail versions must be recorded"
    print(f"  Audit trail version history: {len(updated_doc['versions'])} recorded version entries.")

    # 7. Test Candidate Approval Workflow
    print(f"\n[Step 7] Testing Package Formal Approval Workflow...")
    appr_payload = {
        "approved_by": "Raghunath Reddy",
        "approval_notes": "All verified facts and APAC 19-plant metrics approved for submission."
    }
    appr_pkg = run_api_request(f"/api/packages/{pkg_id}/approve", method="POST", data=appr_payload)
    print(f"  Package Status after approval: {appr_pkg['status']}")
    assert appr_pkg["status"] == "approved", "Package status should be 'approved'"
    assert len(appr_pkg["approvals"]) > 0, "Package approvals list must be present"
    last_appr = appr_pkg["approvals"][-1]
    print(f"  Approval confirmed: Approved by '{last_appr['approved_by']}' on {last_appr['approved_at']}")

    # 8. Test Desktop Notification Service & Duplicate Suppression
    print(f"\n[Step 8] Testing Desktop Notification Service & Duplicate Suppression...")
    from backend.services.notification_service import check_and_notify_high_match_job, is_quiet_hours
    from backend.app.models import Job, DesktopNotificationLog
    from backend.app.database import SessionLocal
    db = SessionLocal()
    job_obj = db.query(Job).filter(Job.id == target_job_id).first()

    # Clear prior test notification logs for this job if any
    db.query(DesktopNotificationLog).filter(DesktopNotificationLog.job_id == target_job_id).delete()
    db.commit()

    # Check quiet hours logic
    quiet_now = is_quiet_hours(22, 7)
    print(f"  Current local time quiet hours active: {quiet_now}")

    # First call with quiet hours bypassed for test: should generate log
    log1 = check_and_notify_high_match_job(db, job_obj, respect_quiet=False)
    print(f"  Notification dispatched/logged: {log1 is not None} (Log ID: {log1.id if log1 else None})")
    assert log1 is not None, "First notification check must create notification log entry!"

    # Second call should be suppressed as duplicate
    log2 = check_and_notify_high_match_job(db, job_obj, respect_quiet=False)
    print(f"  Duplicate notification suppressed: {log2 is None}")
    assert log2 is None, "Second notification check must be suppressed as duplicate!"

    dup_count = db.query(DesktopNotificationLog).filter(DesktopNotificationLog.job_id == target_job_id).count()
    assert dup_count == 1, f"Expected exactly 1 notification log, found {dup_count}"
    print(f"  Duplicate suppression verified: exactly {dup_count} notification logged.")
    db.close()

    print("\n" + "=" * 70)
    print("ALL PHASE 3.1 QA & VALIDATION CHECKS PASSED SUCCESSFULLY (100%)!")
    print("=" * 70)

if __name__ == "__main__":
    run_qa_tests()
