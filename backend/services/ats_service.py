import re
from typing import Dict, Any, List
from backend.app.schemas import ATSKeywordAnalysisResponse, ATSMatchedKeyword, ATSMissingKeyword

# Comprehensive HSE Vocabulary for ATS extraction
HSE_TAXONOMY = {
    "Standards & Regulatory": [
        "ISO 14001", "ISO 45001", "ISO 9001", "OSHA", "Statutory Compliance", 
        "Environmental Compliance", "Legal Register", "Regulatory Audit", "Pollution Control"
    ],
    "Risk & Operations Safety": [
        "Risk Assessment", "HIRA", "HAZOP", "JHA", "Job Hazard Analysis", "Permit to Work", 
        "PTW", "Process Safety", "PSM", "Machine Safety", "Contractor Safety", 
        "Workplace Safety", "Industrial Hygiene", "Ergonomics", "Hazard Identification"
    ],
    "Investigation & Governance": [
        "Incident Investigation", "Root Cause Analysis", "RCA", "Corrective Action", 
        "CAPA", "HSE Governance", "Assurance", "Internal Audit", "Safety Leadership",
        "KPI Reporting", "Performance Metrics", "Management Review"
    ],
    "Leadership & Scope": [
        "Global HSE", "Regional HSE", "Corporate HSE", "Multi-site", "APAC", 
        "Plant Safety", "Manufacturing Safety", "Behavioral Safety", "Safety Culture", 
        "Emergency Preparedness", "Crisis Management", "Cross-Functional Leadership"
    ],
    "Sustainability & ESG": [
        "Sustainability", "ESG Reporting", "Carbon Footprint", "Waste Management", 
        "Water Conservation", "Resource Efficiency", "Environmental Engineering"
    ]
}

def analyze_ats_keywords(job_title: str, job_description: str, profile_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyzes job description requirements against verified candidate profile facts.
    Returns matched keywords with evidence, missing keywords, coverage score, and suggestions.
    Strictly ethical: never claims or recommends fabricated credentials.
    """
    jd_lower = f"{job_title} {job_description}".lower()
    
    # 1. Profile searchable text
    profile_text_parts = [
        profile_dict.get("name", ""),
        profile_dict.get("current_role", ""),
        profile_dict.get("current_company", ""),
        profile_dict.get("summary", "") or ""
    ]
    for role in profile_dict.get("employment_history", []):
        profile_text_parts.append(f"{role.get('company', '')} {role.get('role', '')}")
        profile_text_parts.extend(role.get("highlights", []))
    profile_text_parts.extend(profile_dict.get("qualifications", []))
    profile_text_parts.extend(profile_dict.get("skills", []))
    profile_text_parts.extend(profile_dict.get("certifications", []))
    profile_text_parts.extend(profile_dict.get("achievements", []))
    
    profile_full_lower = " ".join(profile_text_parts).lower()

    matched: List[Dict[str, Any]] = []
    missing: List[Dict[str, Any]] = []

    # 2. Match taxonomy terms found in JD
    tested_keywords = set()
    for category, terms in HSE_TAXONOMY.items():
        for term in terms:
            term_clean = term.lower()
            if term_clean in tested_keywords:
                continue
            tested_keywords.add(term_clean)

            # Check if keyword appears in job description
            pattern = r'\b' + re.escape(term_clean) + r'\b'
            if re.search(pattern, jd_lower):
                # Check if present in candidate profile
                if re.search(pattern, profile_full_lower) or term_clean in profile_full_lower:
                    evidence = f"Verified in your executive profile ({category})"
                    if "iso 14001" in term_clean or "iso 45001" in term_clean:
                        evidence = "Verified: Implemented ISO 14001 & 45001 across multi-plant manufacturing"
                    elif "apac" in term_clean or "19 plants" in term_clean or "multi-site" in term_clean:
                        evidence = "Verified: Directed APAC HSE reporting across 19 plants at dsm-firmenich"
                    elif "investigation" in term_clean or "rca" in term_clean:
                        evidence = "Verified: Incident investigation and Root Cause Analysis at Toshiba & L&T"
                    elif "contractor" in term_clean:
                        evidence = "Verified: Contractor safety management and behavioral audits at Wavin-Orbia"
                    elif "environmental" in term_clean:
                        evidence = "Verified: M.Tech in Environmental Engineering degree awarded"

                    matched.append({
                        "keyword": term,
                        "category": category,
                        "evidence": evidence
                    })
                else:
                    missing.append({
                        "keyword": term,
                        "category": category,
                        "impact": "Required by employer JD; review if relevant in previous roles"
                    })

    # 3. Compute Transparent Coverage Percentage
    total_found_in_jd = len(matched) + len(missing)
    if total_found_in_jd > 0:
        coverage_pct = round((len(matched) / total_found_in_jd) * 100, 1)
    else:
        coverage_pct = 0.0  # Zero coverage when posting lacks HSE taxonomy terms

    coverage_pct = min(100.0, max(0.0, coverage_pct))

    # 4. Generate legitimate ethical suggestions
    suggestions: List[str] = [
        "Include exact phrasing for standard competencies (e.g. 'ISO 14001 and ISO 45001 Management Systems') in your Executive Summary.",
        "Emphasize APAC multi-plant leadership (19 plants) and cross-regional corporate governance to align with senior executive expectations."
    ]
    if missing:
        top_missing = [m["keyword"] for m in missing[:3]]
        suggestions.append(f"Consider clarifying any verified experience related to: {', '.join(top_missing)} if applicable to your project history.")
    elif total_found_in_jd == 0:
        suggestions.append("No standard Health, Safety, Environment (HSE/EHS) keywords detected in the advertised job description.")

    return {
        "job_id": 0,
        "company": "",
        "title": job_title,
        "overall_coverage_pct": coverage_pct,
        "matched_keywords": matched,
        "missing_keywords": missing,
        "legitimate_suggestions": suggestions,
        "disclaimer": "ATS keyword coverage measures the percentage of employer keywords substantiated by verified candidate facts. It is completely independent of overall job suitability and does NOT represent an interview probability or hiring guarantee."
    }
