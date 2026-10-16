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
    summary = (
        f"{name} is an accomplished Senior Health, Safety, and Environment executive with over {years}+ years "
        f"of verifiable leadership experience driving {focus} across complex manufacturing environments. "
        f"Proven track record spearheading HSE governance across 19 manufacturing plants in APAC for global multinational "
        f"organizations including dsm-firmenich. Holds an M.Tech in Environmental Engineering, B.Tech in Mechanical Engineering, "
        f"MBA in Human Resources, and Diploma in Industrial Safety, offering {job_company} an authoritative balance of "
        f"engineering rigor, statutory compliance, and strategic safety culture transformation as {job_title}."
    )

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
        contact_email="raghunath.hse@gmail.com",
        contact_phone="+91 98490 00000",
        contact_location=profile.get("location", "Hyderabad, India"),
        contact_linkedin="linkedin.com/in/raghunath-reddy-hse",
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

    p1 = (
        f"I am writing to express my strong interest in the {job_title} position at {job_company}. "
        f"With over {years}+ years of distinguished leadership directing occupational health, safety, and environmental (HSE) "
        f"programs across complex multi-plant manufacturing footprints in APAC and internationally, I bring a proven track record "
        f"of establishing zero-harm cultures, driving rigorous compliance, and aligning safety governance with core business objectives."
    )

    p2 = (
        f"In my current role as Global SHE & Security Manager at dsm-firmenich, I lead comprehensive SHE performance reporting "
        f"and statutory assurance across 19 manufacturing plants throughout APAC. My career is distinguished by establishing standardized "
        f"ISO 14001 and ISO 45001 management systems, spearheading comprehensive contractor safety management programs, and executing "
        f"meticulous incident investigations using Root Cause Analysis (RCA). Holding an M.Tech in Environmental Engineering, a B.Tech in "
        f"Mechanical Engineering, an MBA in HR, and a Diploma in Industrial Safety, I blend technical engineering discipline with strategic "
        f"people leadership."
    )

    p3 = (
        f"{job_company}'s commitment to operational excellence and employee wellbeing resonates deeply with my professional values. "
        f"I welcome the opportunity to discuss how my multinational governance experience and hands-on plant safety leadership can "
        f"deliver immediate value to your HSE programs. Thank you for your consideration, and I look forward to speaking with your team."
    )

    return TailoredCoverLetterContent(
        candidate_name=name,
        candidate_contact=f"{profile.get('location', 'Hyderabad, India')} | +91 98490 00000 | raghunath.hse@gmail.com",
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
    """
    Coordinates tailored CV generation. Calls Gemini if consent is given and key is active;
    otherwise falls back to deterministic rules-based generator.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if consent_given and api_key:
        prompt = f"""
You are an executive resume specialist tailoring a verified senior HSE executive CV for a specific vacancy.
CANDIDATE FACTS (AUTHORITATIVE, NEVER FABRICATE OUTSIDE THESE FACTS):
Name: {profile.get('name', 'Raghunath Reddy')}
Current Role: {profile.get('current_role')} at {profile.get('current_company')}
Total HSE Experience: {profile.get('experience_years', 18)}+ years
Degrees: M.Tech Environmental Engineering (completed, awarded), B.Tech Mechanical Engineering, MBA Human Resources, Diploma in Industrial Safety
ISO Standards: ISO 14001 and ISO 45001 Management Systems
Scope: Directed APAC HSE performance reporting across 19 manufacturing plants.
Verified Companies: dsm-firmenich, Wavin-Orbia, Toshiba/TLI, Larsen & Toubro, Dharti Dredging.

VACANCY TARGET:
Company: {job_company}
Title: {job_title}
Job Description:
{job_desc[:2500]}

STRICT RULES:
1. Do NOT invent new certifications, employers, dates, metrics, or degrees.
2. Rewrite the professional summary tailored to {job_company} as {job_title} highlighting verified APAC 19-plant scope and environmental engineering credentials.
3. Select and order the top 10 core competencies from candidate's verified skills that match the vacancy.

OUTPUT STRICT VALID JSON ONLY matching this structure:
{{
  "summary": "...",
  "core_competencies": ["..."],
  "evidence_notes": {{"tailoring_focus": "..."}}
}}
"""
        try:
            ai_res = await call_gemini_api_safe(prompt)
            if ai_res and "summary" in ai_res:
                base = generate_tailored_cv_rules(profile, job_company, job_title, job_desc, template_name)
                base.summary = ai_res.get("summary", base.summary)
                if ai_res.get("core_competencies"):
                    base.core_competencies = ai_res["core_competencies"][:10]
                base.generation_method = "ai"
                base.evidence_notes = ai_res.get("evidence_notes", {"source": "Gemini AI tailored based on verified profile"})
                return base
        except Exception as exc:
            logger.warning(f"AI CV tailoring failed, falling back to rules engine: {exc}")

    return generate_tailored_cv_rules(profile, job_company, job_title, job_desc, template_name)

async def generate_tailored_cover_letter(profile: Dict[str, Any], job_company: str, job_title: str, job_location: str, job_desc: str, template_name: str = "global_regional_hse", consent_given: bool = False) -> TailoredCoverLetterContent:
    """
    Coordinates cover letter generation. Uses Gemini if consent & key available, otherwise rules.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if consent_given and api_key:
        prompt = f"""
Write an executive cover letter (250-320 words, 3 concise paragraphs) for {profile.get('name', 'Raghunath Reddy')} applying for {job_title} at {job_company}.
Use ONLY verified facts:
- 18+ years HSE leadership across APAC manufacturing.
- Currently Global SHE & Security Manager at dsm-firmenich managing HSE reporting across 19 plants.
- M.Tech in Environmental Engineering, B.Tech in Mechanical Engineering, MBA HR, Diploma Industrial Safety.
- Deep expertise in ISO 14001, ISO 45001, contractor safety, and Root Cause Analysis (RCA).
Never fabricate company initiatives or false credentials.

OUTPUT STRICT VALID JSON ONLY:
{{
  "paragraph_1": "...",
  "paragraph_2": "...",
  "paragraph_3": "..."
}}
"""
        try:
            ai_res = await call_gemini_api_safe(prompt)
            if ai_res and "paragraph_1" in ai_res:
                base = generate_tailored_cover_letter_rules(profile, job_company, job_title, job_location, template_name)
                base.body_paragraphs = [
                    ai_res["paragraph_1"],
                    ai_res["paragraph_2"],
                    ai_res["paragraph_3"]
                ]
                base.generation_method = "ai"
                return base
        except Exception as exc:
            logger.warning(f"AI cover letter generation failed, falling back to rules engine: {exc}")

    return generate_tailored_cover_letter_rules(profile, job_company, job_title, job_location, template_name)
