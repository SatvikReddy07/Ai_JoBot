import os
import sys
import json
from datetime import datetime

# Set up paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# Set UTF-8 encoding for standard output
sys.stdout.reconfigure(encoding='utf-8')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.models import Job, Base, SearchPreference
from backend.services.matcher import HSEJobMatcher, OccupationalCategory

db_path = os.path.join(project_root, "data", "hse_career.db")
engine = create_engine(f"sqlite:///{db_path}")
SessionLocal = sessionmaker(bind=engine)

def recalculate_and_seed():
    db = SessionLocal()
    matcher = HSEJobMatcher()

    # Step 1: Recalculate all existing jobs in the database
    existing_jobs = db.query(Job).all()
    print(f"Total existing jobs found in database: {len(existing_jobs)}")

    score_distribution = {}
    category_distribution = {}
    audit_records = []
    stripe_record = None

    for job in existing_jobs:
        old_score = job.match_score
        old_level = job.match_level

        res = matcher.evaluate(
            title=job.title,
            location=job.location or "Unknown",
            country=job.country,
            city=job.city,
            employment_type=job.employment_type or "Unknown",
            is_permanent_fulltime=bool(job.is_permanent_fulltime),
            description=job.description or ""
        )

        job.match_score = res.score
        job.match_level = res.level
        job.match_reasons = json.dumps(res.reasons)
        job.matching_qualifications = json.dumps(res.matching_qualifications)
        job.matching_experience = json.dumps(res.matching_experience)
        job.matching_skills = json.dumps(res.matching_skills)
        job.missing_requirements = json.dumps(res.missing_requirements)
        job.location_suitability = res.location_suitability
        job.sponsorship_status = res.sponsorship_status

        score_distribution[res.level] = score_distribution.get(res.level, 0) + 1
        category_distribution[res.occupational_category] = category_distribution.get(res.occupational_category, 0) + 1

        audit_entry = {
            "job_id": job.id,
            "title": job.title,
            "company": job.company,
            "category": res.occupational_category,
            "old_score": old_score,
            "new_score": res.score,
            "old_level": old_level,
            "new_level": res.level,
            "breakdown": res.score_breakdown
        }
        audit_records.append(audit_entry)

        if "Stripe" in (job.company or "") and "Engineering Manager" in (job.title or ""):
            stripe_record = audit_entry

    db.commit()

    print("\n" + "=" * 80)
    print("RECALCULATION COMPLETE ACROSS ALL DATABASE VACANCIES")
    print("=" * 80)
    print("\nScore Distribution:")
    for lvl, cnt in sorted(score_distribution.items()):
        print(f"  - {lvl:<32}: {cnt} jobs")

    print("\nOccupational Category Classification Distribution:")
    for cat, cnt in sorted(category_distribution.items()):
        print(f"  - {cat:<48}: {cnt} jobs")

    if stripe_record:
        print("\n" + "-" * 80)
        print("[AUDIT SPOTLIGHT: Stripe False Positive Remediation]")
        print(f"  Position: {stripe_record['title']} at {stripe_record['company']}")
        print(f"  Category: {stripe_record['category']}")
        print(f"  Old Suitability Score: {stripe_record['old_score']}% ({stripe_record['old_level']})")
        print(f"  New Suitability Score: {stripe_record['new_score']}% ({stripe_record['new_level']})")
        print(f"  Score Breakdown: {stripe_record['breakdown']}")
        print("-" * 80)

    # Step 2: Test 10 Required Representative Vacancy Examples
    print("\n" + "=" * 80)
    print("TESTING 10 REPRESENTATIVE POSITIONS (PRIORITY 1.F TEST MATRIX)")
    print("=" * 80)

    test_matrix = [
        {
            "title": "Regional HSE Manager",
            "company": "Shell Global Operations",
            "desc": "Lead regional health, safety and environmental assurance across manufacturing and terminal operations. Oversee ISO 14001 and ISO 45001 compliance, incident investigation, RCA, and regulatory safety registers.",
            "loc": "Singapore",
            "country": "Singapore"
        },
        {
            "title": "Global EHS Director",
            "company": "GlaxoSmithKline (GSK)",
            "desc": "Direct global EHS strategic roadmap across 20+ multinational plants. Oversee safety culture transformation, zero-harm initiatives, process safety management (PSM), HAZOP reviews, and statutory compliance.",
            "loc": "Singapore / Hyderabad",
            "country": "Singapore"
        },
        {
            "title": "Manufacturing EHS Manager",
            "company": "BASF Chemical",
            "desc": "Lead plant EHS operations, contractor safety management, permit to work (PTW), machine safety, chemical exposure monitoring, and ISO 45001 internal safety audits.",
            "loc": "Ludwigshafen, Germany",
            "country": "Germany"
        },
        {
            "title": "Process Safety Manager",
            "company": "ExxonMobil",
            "desc": "Direct process safety management (PSM), quantitative risk assessment, HAZOP, HIRA, fire protection systems, and chemical process hazards analysis for heavy industrial manufacturing.",
            "loc": "Rotterdam, Netherlands",
            "country": "Netherlands"
        },
        {
            "title": "Environmental Compliance Manager",
            "company": "Unilever Operations",
            "desc": "Manage statutory environmental compliance, ISO 14001 audit protocols, air emissions, wastewater treatment, hazardous waste disposal, and pollution control registers.",
            "loc": "Mumbai, India",
            "country": "India"
        },
        {
            "title": "Corporate HSW Manager",
            "company": "AstraZeneca",
            "desc": "Direct corporate health, safety and wellbeing (HSW) frameworks, occupational ergonomics, employee mental health, and behavior-based safety (BBS) programs across global offices and laboratories.",
            "loc": "Dublin, Ireland",
            "country": "Ireland"
        },
        {
            "title": "Global Sustainability & HSE Manager",
            "company": "Danone",
            "desc": "Lead combined sustainability and HSE reporting. Drive carbon footprint reduction, ESG compliance, Enablon reporting, and ISO 14001 environmental safety frameworks.",
            "loc": "Paris / Amsterdam",
            "country": "Netherlands"
        },
        {
            "title": "Software Engineering Manager",
            "company": "Google",
            "desc": "Lead a team of full-stack software engineers building distributed cloud microservices in Go, Python, and TypeScript. Manage sprints and architecture.",
            "loc": "Bangalore, India",
            "country": "India"
        },
        {
            "title": "IT Project Manager",
            "company": "Salesforce",
            "desc": "Manage enterprise cloud CRM implementation projects, budget allocation, agile scrum ceremonies, and IT vendor deliverables.",
            "loc": "Sydney, Australia",
            "country": "Australia"
        },
        {
            "title": "Sales Director - Enterprise Tech",
            "company": "Snowflake",
            "desc": "Lead enterprise cloud data warehouse sales team, quota attainment, customer contracts, ARR growth, and strategic deal desk negotiations.",
            "loc": "Singapore",
            "country": "Singapore"
        }
    ]

    print(f"{'Position Title':<38} | {'Category':<32} | {'Score':<6} | {'Level':<24} | {'Relevance'}")
    print("-" * 115)

    test_results = []
    for item in test_matrix:
        res = matcher.evaluate(
            title=item["title"],
            location=item["loc"],
            country=item["country"],
            city="",
            employment_type="Full-time",
            is_permanent_fulltime=True,
            description=item["desc"]
        )
        is_rel = "Relevant (HSE)" if res.occupational_category != OccupationalCategory.UNRELATED else "EXCLUDED (Non-HSE)"
        print(f"{item['title'][:37]:<38} | {res.occupational_category[:31]:<32} | {res.score:<6} | {res.level[:23]:<24} | {is_rel}")
        test_results.append({
            "title": item["title"],
            "company": item["company"],
            "category": res.occupational_category,
            "score": res.score,
            "level": res.level,
            "relevance": is_rel,
            "breakdown": res.score_breakdown
        })

    # Save comprehensive report to JSON for audit trail
    report_data = {
        "audit_timestamp": datetime.utcnow().isoformat(),
        "total_jobs_evaluated": len(existing_jobs),
        "score_distribution": score_distribution,
        "category_distribution": category_distribution,
        "stripe_remediation": stripe_record,
        "test_matrix_results": test_results
    }
    with open("data/recalculation_audit_report.json", "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    print("\nAudit report saved to: data/recalculation_audit_report.json")
    db.close()

if __name__ == "__main__":
    recalculate_and_seed()
