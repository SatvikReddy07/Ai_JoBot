import os
import json
import hashlib
import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..app.models import Job, UserProfile, AIJobAssessment, AIUsageLog
from .matcher import HSEJobMatcher

logger = logging.getLogger(__name__)

# Configurable constants
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
DEFAULT_DAILY_LIMIT = int(os.getenv("AI_DAILY_LIMIT", "50"))

class AIMatchAssessmentSchema(BaseModel):
    match_score: int = Field(ge=0, le=100, description="Overall suitability score from 0 to 100 based on candidate fit")
    application_priority: str = Field(description="Recommended application urgency: High, Medium, or Low")
    career_growth_score: int = Field(ge=0, le=100, description="Growth potential score based on leadership scope and international exposure")
    career_growth_summary: str = Field(description="Strategic analysis of how this role advances Raghunath Reddy's career")
    matching_skills: List[str] = Field(default_factory=list, description="HSE competencies present in both profile and job description")
    missing_requirements: List[str] = Field(default_factory=list, description="Requirements not explicitly evidenced in candidate profile")
    qualification_alignment: List[str] = Field(default_factory=list, description="Assessment of academic degree and certification alignment")
    experience_alignment: List[str] = Field(default_factory=list, description="Assessment of management tier and 18+ years multinational exposure")
    industry_alignment: List[str] = Field(default_factory=list, description="Manufacturing, chemical, operations or corporate sector fit")
    visa_relocation_considerations: str = Field(description="Evidence-based international work authorization and sponsorship analysis")
    reasons_to_apply: List[str] = Field(default_factory=list, description="Key compelling factors favoring application")
    reasons_to_reconsider: List[str] = Field(default_factory=list, description="Potential drawbacks, seniority mismatch, or location hurdles")
    evidence_references: Dict[str, Any] = Field(default_factory=dict, description="Verifiable excerpts from job description and candidate profile")

def compute_job_hash(title: str, location: str, description: str) -> str:
    """Compute SHA-256 hash for vacancy content to support intelligent caching."""
    raw = f"{title.strip().lower()}::{location.strip().lower()}::{description.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def assessment_cache_key(db, job, profile, selected_model=None):
    """No schema change: existing job_hash now signs all assessment inputs."""
    from .matching_context import POLICY_VERSION, match_options
    options = match_options(profile, db)
    vacancy = {name: getattr(job, name) for name in ("title", "company", "location", "city", "country",
        "description", "employment_type", "is_permanent_fulltime", "url", "is_active")}
    content = dict(policy=POLICY_VERSION, vacancy=vacancy, context=options,
        model=selected_model or os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
        api_configured=bool(os.getenv("GEMINI_API_KEY", "").strip()), day=date.today().isoformat())
    return hashlib.sha256(json.dumps(content, sort_keys=True, default=str).encode()).hexdigest()


def cached_assessment_is_current(db, job):
    profile = db.query(UserProfile).first()
    return bool(profile and job.ai_assessment and
                job.ai_assessment.job_hash == assessment_cache_key(db, job, profile))


def get_daily_ai_usage(db: Session, daily_limit: Optional[int] = None) -> Dict[str, Any]:
    """Retrieve daily request counts and quota utilization."""
    if daily_limit is None:
        daily_limit = max(0, int(os.getenv("AI_DAILY_LIMIT", str(DEFAULT_DAILY_LIMIT))))
    today_str = date.today().isoformat()
    count = db.query(AIUsageLog).filter(
        AIUsageLog.daily_date == today_str,
        AIUsageLog.status.in_(["success", "failed", "rate_limited"])
    ).count()

    cached_count = db.query(AIUsageLog).filter(
        AIUsageLog.daily_date == today_str,
        AIUsageLog.status == "cached"
    ).count()

    return {
        "daily_used": count,
        "daily_limit": daily_limit,
        "remaining": max(0, daily_limit - count),
        "cached_today": cached_count,
        "date": today_str,
        "model": DEFAULT_GEMINI_MODEL,
        "api_key_configured": bool(os.getenv("GEMINI_API_KEY", "").strip())
    }

def compute_career_growth_score(job: Job, profile: UserProfile) -> Tuple[int, str]:
    """
    Local heuristic calculation for career growth and organizational opportunity score.
    Considers seniority progression, multi-plant scale, multinational exposure.
    """
    title_lower = job.title.lower()
    desc_lower = job.description.lower()
    score = 60
    factors = []

    # Seniority leap
    if any(k in title_lower for k in ["vice president", "vp", "head of", "director"]):
        score += 20
        factors.append("Executive leadership advancement (Director / VP / Head of level)")
    elif any(k in title_lower for k in ["global", "corporate"]):
        score += 15
        factors.append("Corporate / Global scope aligns with strategic trajectory")
    elif any(k in title_lower for k in ["regional", "apac", "emea"]):
        score += 10
        factors.append("Multi-country regional footprint")

    # Scale and exposure
    if any(k in desc_lower for k in ["multi-site", "multi site", "plants", "global network"]):
        score += 10
        factors.append("Extensive multi-facility operational leadership")

    # International mobility
    if job.country in ["Germany", "Netherlands", "Ireland", "Singapore", "Australia"]:
        score += 10
        factors.append(f"Strategic international career presence in {job.country}")

    score = min(100, max(40, score))
    summary = "; ".join(factors) if factors else "Solid lateral managerial role with continuous HSE assurance scope."
    return score, summary

def generate_fallback_assessment(job: Job, profile: UserProfile, reason_msg: str = "") -> Dict[str, Any]:
    """
    High-fidelity local rules-based assessment used when Gemini API is unconfigured,
    rate-limited, or when user has not enabled external AI consent.
    Explicitly labeled as rules_fallback.
    """
    matcher = HSEJobMatcher()
    from .matching_context import evaluate_job
    result = evaluate_job(job, profile)

    growth_score, growth_summary = compute_career_growth_score(job, profile)

    priority = "Medium"
    if result.score >= 85:
        priority = "High"
    elif result.score < 65:
        priority = "Low"

    reasons_apply = list(result.reasons[:3])
    if result.sponsorship_status == "Confirmed":
        reasons_apply.append("Employer explicitly provides visa / relocation support.")

    reasons_reconsider = []
    if result.sponsorship_status == "Not Supported":
        reasons_reconsider.append("Job description notes local work authorization required (no visa sponsorship).")
    if result.missing_requirements:
        reasons_reconsider.extend(result.missing_requirements[:2])
    if not reasons_reconsider:
        reasons_reconsider.append("Verify whether travel requirements align with personal preferences.")

    disclaimer = reason_msg or "Evaluated using local rules-based engine (100-point model)."

    return {
        "match_score": result.score,
        "application_priority": priority,
        "career_growth_score": growth_score,
        "career_growth_summary": f"{growth_summary} [{disclaimer}]",
        "matching_skills": result.matching_skills,
        "missing_requirements": result.missing_requirements,
        "qualification_alignment": result.matching_qualifications,
        "experience_alignment": result.matching_experience,
        "industry_alignment": ["Industry scope requires comparison with confirmed employment history"],
        "visa_relocation_considerations": (
            f"Location: {job.country or 'Unknown'}. Status: {result.sponsorship_status}. "
            "Note: Evaluated strictly from explicit job advertisement text without unverified assumptions."
        ),
        "reasons_to_apply": reasons_apply,
        "reasons_to_reconsider": reasons_reconsider,
        "evidence_references": {
            "job_title": job.title,
            "company": job.company,
            "location": job.location,
            "matching_points_awarded": result.reasons
        },
        "model_used": "rules_fallback",
        "engine_used": "rules_fallback"
    }

async def analyze_job_with_ai(
    db: Session,
    job: Job,
    profile: UserProfile,
    force_reanalyze: bool = False,
    model_name: Optional[str] = None
) -> AIJobAssessment:
    """
    Main AI assessment orchestrator:
    1. Checks user privacy consent.
    2. Checks cached analysis via SHA-256 hash.
    3. Checks daily rate limit quota.
    4. Calls Gemini SDK with structured schema.
    5. Falls back safely if API is unavailable, unconfigured, or rate limited.
    """
    selected_model = model_name or os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    job_hash = assessment_cache_key(db, job, profile, selected_model)
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    today_str = date.today().isoformat()

    # Local occupational gating cannot be overridden by an AI response.
    matcher = HSEJobMatcher()
    _, relevant, _ = matcher.classify_occupational_relevance(job.title, job.description or "")
    excluded, _ = matcher.is_excluded(job.title, job.description or "", job.employment_type or "")
    if not relevant or excluded or not job.is_active:
        data = generate_fallback_assessment(job, profile, "Excluded or inactive vacancy; no AI request sent.")
        data["application_priority"] = "Low"
        if excluded or not job.is_active: data["match_score"] = min(data["match_score"], 15)
        return _upsert_assessment(db, job.id, job_hash, data)

    # 1. Check existing cached assessment
    existing_assessment = db.query(AIJobAssessment).filter(AIJobAssessment.job_id == job.id).first()
    if existing_assessment and not force_reanalyze:
        retryable_fallback = existing_assessment.engine_used != "ai" and profile.consent_given_for_ai and bool(api_key)
        if existing_assessment.job_hash == job_hash and not retryable_fallback:
            logger.info(f"Returning cached assessment for Job #{job.id} ({job.title}).")
            # Log cache hit
            log_entry = AIUsageLog(
                timestamp=datetime.utcnow(),
                job_id=job.id,
                model=existing_assessment.model_used,
                status="cached",
                daily_date=today_str
            )
            db.add(log_entry)
            db.commit()
            return existing_assessment

    # 2. Privacy Consent Check
    if not profile.consent_given_for_ai:
        logger.info(f"AI consent not given by user. Using local rules fallback for Job #{job.id}.")
        fallback_data = generate_fallback_assessment(
            job, profile,
            reason_msg="External AI consent not enabled in My Career Profile. Local rules engine used."
        )
        return _upsert_assessment(db, job.id, job_hash, fallback_data)

    # 3. Check API Key
    if not api_key:
        logger.info(f"GEMINI_API_KEY not configured in environment. Using rules-based fallback for Job #{job.id}.")
        fallback_data = generate_fallback_assessment(
            job, profile,
            reason_msg="Gemini API key not configured in backend environment. Local rules engine used."
        )
        return _upsert_assessment(db, job.id, job_hash, fallback_data)

    # 4. Check Daily Request Limit
    usage = get_daily_ai_usage(db)
    if usage["daily_used"] >= usage["daily_limit"]:
        logger.warning(f"Daily AI limit ({usage['daily_limit']}) reached. Falling back to rules engine.")
        # Record limit reached in log
        log_entry = AIUsageLog(
            timestamp=datetime.utcnow(),
            job_id=job.id,
            model=selected_model,
            status="quota_skipped",
            daily_date=today_str
        )
        db.add(log_entry)
        db.commit()

        fallback_data = generate_fallback_assessment(
            job, profile,
            reason_msg=f"Daily AI quota limit ({usage['daily_limit']}/day) reached. Local rules engine used."
        )
        return _upsert_assessment(db, job.id, job_hash, fallback_data)

    # 5. Execute Gemini API Call via official google-genai SDK
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        prompt = f"""
You are an expert executive career advisor evaluating Health, Safety, and Environment (HSE/EHS/SHE&S) leadership vacancies for a high-caliber candidate.

CANDIDATE VERIFIED PROFILE:
Name: {profile.name}
Current Role: {profile.current_role} at {profile.current_company}
Total industrial experience: {profile.experience_years} years; distinguish operations/maintenance from HSE leadership using employment history.
Employment history: {profile.employment_history}
Academic Qualifications: {profile.qualifications}
Core Technical Competencies: {profile.skills}
Key Certifications: {profile.certifications}
Candidate-provided track record: {profile.achievements}
Target Geographies: {profile.target_countries}

VACANCY TO ANALYZE:
Company: {job.company}
Job Title: {job.title}
Location: {job.location} (Country: {job.country or 'Unknown'}, City: {job.city or 'Unknown'})
Advertised Employment Type: {job.employment_type}
Job Description:
\"\"\"
{job.description[:4000]}
\"\"\"

EVALUATION DIRECTIVES:
1. Compare the vacancy with only the supplied candidate facts. Never invent degrees, certifications, scope, dates or metrics.
2. Calculate an honest suitability Match Score (0-100). Do NOT treat this as employer hiring probability.
3. Calculate Career Growth Score (0-100) reflecting leadership scope, multinational exposure, and career progression.
4. Distinguish explicit visa sponsorship statements in the job description ('Confirmed', 'Possible', 'Not Supported', or 'Unknown'). Never assume sponsorship merely because the company is multinational.
5. Identify specific technical competencies present and missing requirements.
6. Provide verifiable quotes / excerpts in evidence_references.
"""

        response = client.models.generate_content(
            model=selected_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AIMatchAssessmentSchema,
                temperature=0.2
            )
        )

        raw_json = response.text
        parsed_dict = json.loads(raw_json)
        validated = AIMatchAssessmentSchema(**parsed_dict)

        assessment_data = validated.model_dump()
        assessment_data["model_used"] = selected_model
        assessment_data["engine_used"] = "ai"
        assessment_data["raw_response_json"] = raw_json

        # Log successful AI request
        log_entry = AIUsageLog(
            timestamp=datetime.utcnow(),
            job_id=job.id,
            model=selected_model,
            status="success",
            daily_date=today_str
        )
        db.add(log_entry)
        db.commit()

        logger.info(f"AI assessment completed for Job #{job.id} using {selected_model}. Score: {validated.match_score}")
        return _upsert_assessment(db, job.id, job_hash, assessment_data)

    except Exception as exc:
        logger.error(f"Gemini API execution failed for Job #{job.id}: {exc}", exc_info=True)
        # Log failure
        log_entry = AIUsageLog(
            timestamp=datetime.utcnow(),
            job_id=job.id,
            model=selected_model,
            status="failed",
            daily_date=today_str
        )
        db.add(log_entry)
        db.commit()

        fallback_data = generate_fallback_assessment(
            job, profile,
            reason_msg=f"Gemini API call encountered error ({str(exc)[:60]}). Local rules engine used."
        )
        return _upsert_assessment(db, job.id, job_hash, fallback_data)

def _upsert_assessment(db: Session, job_id: int, job_hash: str, data: Dict[str, Any]) -> AIJobAssessment:
    """Store or update AI assessment in database."""
    assessment = db.query(AIJobAssessment).filter(AIJobAssessment.job_id == job_id).first()

    raw_json = data.get("raw_response_json") or json.dumps(data)

    if not assessment:
        assessment = AIJobAssessment(
            job_id=job_id,
            job_hash=job_hash,
            match_score=data.get("match_score", 0),
            application_priority=data.get("application_priority", "Medium"),
            career_growth_score=data.get("career_growth_score", 0),
            career_growth_summary=data.get("career_growth_summary", ""),
            matching_skills=json.dumps(data.get("matching_skills", [])),
            missing_requirements=json.dumps(data.get("missing_requirements", [])),
            qualification_alignment=json.dumps(data.get("qualification_alignment", [])),
            experience_alignment=json.dumps(data.get("experience_alignment", [])),
            industry_alignment=json.dumps(data.get("industry_alignment", [])),
            visa_relocation_considerations=data.get("visa_relocation_considerations", ""),
            reasons_to_apply=json.dumps(data.get("reasons_to_apply", [])),
            reasons_to_reconsider=json.dumps(data.get("reasons_to_reconsider", [])),
            evidence_references=json.dumps(data.get("evidence_references", {})),
            model_used=data.get("model_used", "gemini-2.5-flash"),
            engine_used=data.get("engine_used", "ai"),
            created_at=datetime.utcnow(),
            raw_response_json=raw_json
        )
        db.add(assessment)
    else:
        assessment.job_hash = job_hash
        assessment.match_score = data.get("match_score", 0)
        assessment.application_priority = data.get("application_priority", "Medium")
        assessment.career_growth_score = data.get("career_growth_score", 0)
        assessment.career_growth_summary = data.get("career_growth_summary", "")
        assessment.matching_skills = json.dumps(data.get("matching_skills", []))
        assessment.missing_requirements = json.dumps(data.get("missing_requirements", []))
        assessment.qualification_alignment = json.dumps(data.get("qualification_alignment", []))
        assessment.experience_alignment = json.dumps(data.get("experience_alignment", []))
        assessment.industry_alignment = json.dumps(data.get("industry_alignment", []))
        assessment.visa_relocation_considerations = data.get("visa_relocation_considerations", "")
        assessment.reasons_to_apply = json.dumps(data.get("reasons_to_apply", []))
        assessment.reasons_to_reconsider = json.dumps(data.get("reasons_to_reconsider", []))
        assessment.evidence_references = json.dumps(data.get("evidence_references", {}))
        assessment.model_used = data.get("model_used", "gemini-2.5-flash")
        assessment.engine_used = data.get("engine_used", "ai")
        assessment.created_at = datetime.utcnow()
        assessment.raw_response_json = raw_json

    db.commit()
    db.refresh(assessment)
    return assessment


async def call_gemini_api_safe(prompt: str, model_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Safe helper to call Gemini API and return parsed JSON dict, or None on failure."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        selected_model = model_name or os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        response = client.models.generate_content(
            model=selected_model,
            contents=prompt,
        )
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except Exception as exc:
        logger.warning(f"call_gemini_api_safe error: {exc}")
        return None

