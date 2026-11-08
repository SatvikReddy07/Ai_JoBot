"""Evidence-based screening. Unknown facts are never converted into eligibility."""
import json
import re
from datetime import date
from .matcher import HSEJobMatcher, OccupationalCategory


def assess_eligibility(job, profile):
    matcher = HSEJobMatcher()
    from .matching_context import evaluate_job
    result = evaluate_job(job, profile)
    checks = []
    def add(category, status, detail, mandatory=False):
        checks.append(dict(category=category, status=status, detail=detail, is_mandatory=mandatory))
    relevant = result.occupational_category != OccupationalCategory.UNRELATED
    excluded, reason = matcher.is_excluded(job.title, job.description or "", job.employment_type or "")
    add("occupational_relevance", "met" if relevant else "not_met",
        result.occupational_category, True)
    add("seniority", "not_met" if excluded else "requires_review",
        reason if excluded else "Review scope against confirmed experience; title alone does not prove fit.", True)
    text = job.description or ""
    # Only explicit mandatory clauses become mandatory gaps. Preferred credentials do not.
    clauses = re.split(r"[.\n;]", text)
    for category, terms in {
        "education": ["bachelor", "master", "m.tech", "b.tech", "degree", "diploma"],
        "certifications": ["nebosh", "csp", "iosh", "professional engineer", "lead auditor"],
        "industry_experience": ["pharmaceutical", "chemical", "manufacturing", "construction", "process safety"]
    }.items():
        found = False
        for clause in clauses:
            if not re.search(r"\b(must|required|mandatory|essential)\b", clause, re.I):
                continue
            for term in terms:
                if re.search(r"\b"+re.escape(term)+r"\b", clause, re.I):
                    found = True
                    # A keyword does not establish the full discipline, level, duration
                    # or license requirement. Only explicit user evidence can resolve it.
                    status = "requires_review"
                    add(category, status, clause.strip(), True)
        if not found:
            add(category, "unknown", "No explicit mandatory requirement identified; review original listing.")
    for category, pattern in {
        "language": r"\b(?:fluent|fluency|native|language)\b",
        "licenses": r"\b(?:licen[cs]e|registration|citizenship|citizen)\b"
    }.items():
        matches = [c.strip() for c in clauses if re.search(pattern, c, re.I)]
        add(category, "requires_review" if matches else "unknown",
            "; ".join(matches) or "Not specified.", bool(matches))
    countries = json.loads(profile.target_countries or "[]")
    add("location", "met" if job.country and job.country in countries else "requires_review",
        f"Vacancy country: {job.country or 'Unknown'}; confirm location preference.")
    sponsor = result.sponsorship_status
    add("visa_sponsorship", "unknown" if sponsor == "Unknown" else "requires_review",
        f"Listing evidence: {sponsor}. Sponsorship does not establish personal eligibility.")
    add("work_authorization", "unknown", "No verified work-rights record. Confirm rights or sponsorship with employer.", True)
    add("employment_type", "met" if job.is_permanent_fulltime else "requires_review", job.employment_type or "Unknown")
    closing = re.search(r"(?:closing date|deadline|apply by)\s*[:\-]?\s*(\d{4}-\d{2}-\d{2})", text, re.I)
    expired = False
    if closing:
        try: expired = date.fromisoformat(closing.group(1)) < date.today()
        except ValueError: pass
    add("closing_date", "not_met" if expired else "requires_review" if closing else "unknown",
        closing.group(1) if closing else "Not supplied in structured data; check listing.", expired)
    if not relevant or excluded or expired or not job.is_active:
        status = "not_eligible"
    elif any(c["is_mandatory"] and c["status"] == "requires_review" for c in checks):
        status = "requires_review"
    else:
        status = "unknown_eligibility"
    return dict(job_id=job.id, company=job.company, title=job.title, overall_status=status,
        checks=checks, match_score=result.score, sponsorship_status=sponsor,
        recommendation="Review unknowns and original requirements before approving preparation.")
