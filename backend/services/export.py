import csv
import io
import json
from typing import List
from ..app.models import Job

def generate_jobs_csv(jobs: List[Job]) -> io.StringIO:
    """
    Generate CSV data for exported jobs.
    """
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Headers
    headers = [
        "Job ID",
        "Company",
        "Job Title",
        "Country",
        "City",
        "Location Raw",
        "Employment Type",
        "Match Score",
        "Match Level",
        "Sponsorship Status",
        "Application Status",
        "Posting Date",
        "Discovered Date",
        "Source",
        "Source Job ID",
        "Application URL",
        "Match Reasons",
        "Matching Skills",
        "Matching Qualifications",
        "Missing Requirements"
    ]
    writer.writerow(headers)

    for j in jobs:
        reasons_str = "; ".join(json.loads(j.match_reasons or "[]"))
        skills_str = "; ".join(json.loads(j.matching_skills or "[]"))
        quals_str = "; ".join(json.loads(j.matching_qualifications or "[]"))
        missing_str = "; ".join(json.loads(j.missing_requirements or "[]"))
        post_date = j.posted_date.strftime("%Y-%m-%d") if j.posted_date else ""
        disc_date = j.discovered_at.strftime("%Y-%m-%d %H:%M") if j.discovered_at else ""

        writer.writerow([
            j.id,
            j.company,
            j.title,
            j.country or "Unknown",
            j.city or "",
            j.location,
            j.employment_type,
            j.match_score,
            j.match_level,
            j.sponsorship_status,
            j.application_status,
            post_date,
            disc_date,
            j.source,
            j.source_job_id,
            j.url,
            reasons_str,
            skills_str,
            quals_str,
            missing_str
        ])

    output.seek(0)
    return output
