import pytest
from backend.app.models import Job
from backend.tests.conftest import TestingSessionLocal, client


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["app"] == "HSE Career Agent"

def test_dashboard_stats_and_settings():
    res_stats = client.get("/api/dashboard/stats")
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert "total_jobs" in stats
    assert "excellent_matches" in stats

    res_settings = client.get("/api/settings")
    assert res_settings.status_code == 200
    settings = res_settings.json()
    assert settings["profile_name"] == "Raghunath Reddy"
    assert "India" in settings["target_countries"]

def test_employer_boards_crud():
    # 1. List employers
    res_list = client.get("/api/employers")
    assert res_list.status_code == 200

    # 2. Create employer
    new_board = {
        "company_name": "Test Company",
        "platform": "greenhouse",
        "board_token": "testcompany",
        "is_enabled": True
    }
    res_create = client.post("/api/employers", json=new_board)
    assert res_create.status_code == 200
    created = res_create.json()
    board_id = created["id"]
    assert created["company_name"] == "Test Company"

    # 3. Update employer
    res_update = client.put(f"/api/employers/{board_id}", json={"is_enabled": False})
    assert res_update.status_code == 200
    assert res_update.json()["is_enabled"] is False

    # 4. Delete employer
    res_del = client.delete(f"/api/employers/{board_id}")
    assert res_del.status_code == 200

def test_save_and_update_application_status():
    db = TestingSessionLocal()
    job = Job(
        source="greenhouse",
        source_job_id="test_101",
        company="Global Agro",
        title="Senior HSE Manager",
        location="Frankfurt, Germany",
        country="Germany",
        city="Frankfurt",
        employment_type="Permanent Full-time",
        is_permanent_fulltime=True,
        description="Lead safety governance.",
        url="https://boards.greenhouse.io/globalagro/jobs/test_101",
        match_score=88,
        match_level="Excellent Match",
        sponsorship_status="Unknown",
        application_status="Discovered",
        is_saved=False
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = job.id
    db.close()

    # Save job
    res_save = client.post(f"/api/jobs/{job_id}/save", json={"is_saved": True})
    assert res_save.status_code == 200
    assert res_save.json()["is_saved"] is True

    # Update application status
    res_status = client.put(f"/api/jobs/{job_id}/status", json={"status": "Applied", "notes": "Submitted with tailored CV"})
    assert res_status.status_code == 200
    assert res_status.json()["current_status"] == "Applied"

    # Export CSV
    res_csv = client.get("/api/jobs/export")
    assert res_csv.status_code == 200
    assert "Global Agro" in res_csv.text
    assert "Senior HSE Manager" in res_csv.text
