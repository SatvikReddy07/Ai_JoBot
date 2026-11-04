import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

from backend.app.schemas import TailoredCVContent, TailoredCoverLetterContent, EmploymentHistoryItem
from backend.services.gemini_service import call_gemini_api_safe

logger = logging.getLogger(__name__)

TEMPLATE_CONFIGS = {
    "global_regional_hse": {
        "title": "Global / Regional HSE Leadership",
        "focus_summary": "corporate governance, cross-regional HSE assurance, and APAC multi-plant manufacturing safety",
        "priority_skills": [
            "Corporate and Global HSE Management",
            "Regional and APAC HSE Leadership",
            "HSE Performance Reporting & Analytics",
            "Workplace Health and Safety Governance",
            "ISO 14001 & ISO 45001 Management Systems",
            "Sustainability and ESG Reporting"
        ]
    },
    "manufacturing_industrial_ehs": {
        "title": "Manufacturing / Industrial EHS Leadership",
        "focus_summary": "high-hazard manufacturing plant safety, process safety management, contractor safety audits, and incident prevention",
        "priority_skills": [
            "Risk Assessment & Management (HAZOP / HIRA / JHA)",
            "Contractor Safety Management",
            "Incident Investigation & Root Cause Analysis (RCA)",
            "Machine Safety & Plant Safety Governance",
            "Statutory Compliance & Legal Registers",
            "ISO 14001 & ISO 45001 Management Systems"
        ]
    },
    "corporate_workplace_hse": {
        "title": "Corporate / Workplace HSE Leadership",
        "focus_summary": "enterprise workplace health & safety culture, statutory compliance audits, behavioral safety programs, and executive risk governance",
        "priority_skills": [
            "Workplace Health and Safety Governance",
            "Employee Health, Wellness & Safety Culture",
            "HSE Audits and Statutory Compliance",
            "Corporate and Global HSE Management",
            "Contractor Safety Management",
            "Incident Investigation & Root Cause Analysis (RCA)"
        ]
    }
}

def generate_tailored_cv_rules(profile: Dict[str, Any], job_company: str, job_title: str, job_desc: str, template_name: str = "global_regional_hse") -> TailoredCVContent:
    """
    Deterministic rules-based CV tailoring using 100% verified profile facts.
    Never invents facts.
    """
    cfg = TEMPLATE_CONFIGS.get(template_name, TEMPLATE_CONFIGS["global_regional_hse"])
    focus = cfg["focus_summary"]
    years = profile.get("experience_years", 18)
    name = profile.get("name", "Raghunath Reddy")

    # Tailored Executive Summary
    summary = profile.get("summary") or " ".join(filter(None, [
        name, profile.get("current_role", ""), profile.get("current_company", "")
    ]))

    summary += f" Target position: {job_title} at {job_company}."

    # Reorder competencies to prioritize template & JD matches
    all_skills = list(profile.get("skills", []))
    priority = [s for s in cfg["priority_skills"] if s in all_skills]
    remainder = [s for s in all_skills if s not in priority]
    ordered_skills = priority + remainder

    # Employment history with ordered bullet highlights
    raw_history = profile.get("employment_history", [])
    history_items = []
    for h in raw_history:
        history_items.append(EmploymentHistoryItem(
            company=h.get("company", ""),
            role=h.get("role", ""),
            location=h.get("location", ""),
            highlights=list(h.get("highlights", [])),
            source=h.get("source", "verified_profile")
        ))

    return TailoredCVContent(
        name=name,
        headline=f"{job_title} | Senior HSE Executive",
        contact_email=profile.get("contact_email", ""),
        contact_phone=profile.get("contact_phone", ""),
        contact_location=profile.get("location", ""),
        contact_linkedin=profile.get("contact_linkedin", ""),
        summary=summary,
        core_competencies=ordered_skills[:10],
        employment_history=history_items,
        education=list(profile.get("qualifications", [])),
        certifications=list(profile.get("certifications", [])),
        key_achievements=list(profile.get("achievements", [])),
        template_name=template_name,
        target_job_title=job_title,
        target_company=job_company,
        generation_method="rules_fallback",
        evidence_notes={
            "summary_source": "Verified candidate profile & template focus",
            "skills_source": "Confirmed competency inventory re-ranked for vacancy alignment",
            "experience_source": "Authoritative employment history from master CV"
        }
    )

def generate_tailored_cover_letter_rules(profile: Dict[str, Any], job_company: str, job_title: str, job_location: str, template_name: str = "global_regional_hse") -> TailoredCoverLetterContent:
    """
    Deterministic rules-based executive cover letter generation (approx 250-320 words).
    """
    name = profile.get("name", "Raghunath Reddy")
    years = profile.get("experience_years", 18)
    today_str = datetime.now().strftime("%B %d, %Y")

    # Include only values in the reviewed profile; no fixed employer/degree claims.
    p1 = (f"I am writing to express my interest in the {job_title} position at {job_company}. "
          "Please find my tailored CV attached for your review. I would welcome the opportunity "
          "to discuss the responsibilities of the position and the experience most relevant to your team.")
    facts = "; ".join(filter(None, [profile.get("current_role"), profile.get("current_company"),
                                 profile.get("summary")]))
    p2 = "My confirmed professional background: " + facts
    p3 = ("I would appreciate the opportunity to discuss the position, its priorities and the qualifications "
          "required for success. I am happy to clarify any part of my experience and provide supporting "
          "information during your selection process. Please review my CV alongside this letter for the "
          "specific roles, skills and qualifications I have provided. I would also welcome a discussion "
          "about the location, work arrangements and any work authorization requirements that apply to "
          "the vacancy. Thank you for considering my application and for taking the time to review my "
          "background. I look forward to hearing from your team about the appropriate next steps.")

    return TailoredCoverLetterContent(
        candidate_name=name,
        candidate_contact=" | ".join(filter(None, [profile.get("location"), profile.get("contact_phone"), profile.get("contact_email")])),
        date_str=today_str,
        hiring_manager="Hiring Team",
        company_name=job_company,
        job_title=job_title,
        salutation=f"Dear Hiring Team at {job_company},",
        body_paragraphs=[p1, p2, p3],
        sign_off=f"Sincerely,\n{name}",
        generation_method="rules_fallback"
    )

async def generate_tailored_cv(profile: Dict[str, Any], job_company: str, job_title: str, job_desc: str, template_name: str = "global_regional_hse", consent_given: bool = False) -> TailoredCVContent:
    # Deterministic generation preserves reviewed facts. AI job matching remains optional.
    return generate_tailored_cv_rules(profile, job_company, job_title, job_desc, template_name)

async def generate_tailored_cover_letter(profile: Dict[str, Any], job_company: str, job_title: str, job_location: str, job_desc: str, template_name: str = "global_regional_hse", consent_given: bool = False) -> TailoredCoverLetterContent:
    return generate_tailored_cover_letter_rules(profile, job_company, job_title, job_location, template_name)
