import re
import json
from typing import Dict, List, Any, Optional, Tuple

class OccupationalCategory:
    HSE_LEADERSHIP = "HSE / EHS / SHE / HSW Leadership"
    PROCESS_INDUSTRIAL_SAFETY = "Process Safety / Industrial Safety"
    ENVIRONMENTAL_COMPLIANCE = "Environmental Compliance / Environmental Management"
    SUSTAINABILITY_ESG = "Sustainability / ESG with HSE Relevance"
    CORPORATE_WORKPLACE_SAFETY = "Corporate / Workplace Safety"
    ADJACENT = "Adjacent but potentially relevant"
    UNRELATED = "Unrelated"

class MatchResult:
    def __init__(
        self,
        score: int,
        level: str,
        reasons: List[str],
        matching_qualifications: List[str],
        matching_experience: List[str],
        matching_skills: List[str],
        missing_requirements: List[str],
        location_suitability: str,
        sponsorship_status: str,
        occupational_category: str = OccupationalCategory.UNRELATED,
        score_breakdown: Optional[Dict[str, int]] = None
    ):
        self.score = score
        self.level = level
        self.reasons = reasons
        self.matching_qualifications = matching_qualifications
        self.matching_experience = matching_experience
        self.matching_skills = matching_skills
        self.missing_requirements = missing_requirements
        self.location_suitability = location_suitability
        self.sponsorship_status = sponsorship_status
        self.occupational_category = occupational_category
        self.score_breakdown = score_breakdown or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "level": self.level,
            "reasons": self.reasons,
            "matching_qualifications": self.matching_qualifications,
            "matching_experience": self.matching_experience,
            "matching_skills": self.matching_skills,
            "missing_requirements": self.missing_requirements,
            "location_suitability": self.location_suitability,
            "sponsorship_status": self.sponsorship_status,
            "occupational_category": self.occupational_category,
            "score_breakdown": self.score_breakdown
        }

class HSEJobMatcher:
    """
    Explainable, rules-based matching engine for Raghunath Reddy's HSE executive profile.
    Total Score: 100 points maximum across 6 explainable dimensions:
    - 1. Occupational Relevance: 25 pts (Mandatory relevance gate)
    - 2. Seniority Alignment: 20 pts (Executive & multi-site leadership)
    - 3. HSE Technical Competencies: 25 pts (ISO 14001/45001, RCA, PSM, Audits)
    - 4. Industry Alignment: 10 pts (Manufacturing, chemical, operations)
    - 5. Educational Qualifications: 10 pts (M.Tech Env, B.Tech Mech, Safety Diploma, Lead Auditor)
    - 6. Location & International Preference: 10 pts (India, Singapore, Europe, Australia)
    """

    # Exclusions
    EXCLUDED_PATTERNS = [
        r"\bintern\b", r"\binternship\b", r"\bgraduate trainee\b",
        r"\bsafety officer\b", r"\bjunior safety officer\b", r"\bfire officer\b",
        r"\btechnician\b", r"\bfreelance\b", r"\bconsultancy contract\b",
        r"\btemp\b", r"\btemporary assignment\b"
    ]

    # Target Leadership Title Keywords
    GLOBAL_REGIONAL_TITLES = [
        "global", "corporate", "regional", "head of", "director", "vice president", "vp",
        "lead", "apac", "emea", "group"
    ]

    HSE_CORE_TITLE_PATTERNS = [
        r"\bohs\b", r"\bwhs\b", r"\bhsse\b", r"\beh&s\b",
        r"\bhealth\s*,\s*safety\s*(?:and|&)\s*environment(?:al)?\b",
        r"\bhse\b", r"\behs\b", r"\bshe\b", r"\bshe&s\b", r"\bhsw\b", r"\bqhse\b",
        r"\bhealth\s*(and|&)\s*safety\b", r"\bworkplace\s*health\b", r"\bworkplace\s*safety\b",
        r"\boccupational\s*health\b", r"\boccupational\s*safety\b", r"\benvironment(al)?\s*health\b",
        r"\bsafety\s*(and|&)\s*environment\b", r"\bprocess\s*safety\b", r"\bindustrial\s*safety\b",
        r"\bsafety\s*manager\b", r"\bsafety\s*director\b", r"\bsafety\s*lead\b", r"\bhead\s*of\s*safety\b",
        r"\bsustainability\s*(and|&)\s*safety\b", r"\benvironmental\s*manager\b",
        r"\bsafety\s*assurance\b", r"\bsafety\s*governance\b", r"\behs\s*manager\b", r"\bhse\s*manager\b"
    ]

    # Explicit Non-HSE Domain Titles (Strictly Disqualified from HSE Matches)
    NON_OCCUPATIONAL_SAFETY_PATTERNS = [
        r"\benvironmental\s*test(?:ing)?\b",
        r"\btrust\s*(?:and|&)\s*safety\b", r"\bfunctional\s*safety\b",
        r"\bsystems?\s*(?:and\s*)?safety\b",
    ]
    NON_HSE_DOMAINS = NON_OCCUPATIONAL_SAFETY_PATTERNS + [
        r"\bsoftware\b", r"\bfrontend\b", r"\bbackend\b", r"\bfull\s*stack\b", r"\bdevops\b",
        r"\bcloud\b", r"\bdata\s*engineer\b", r"\bdata\s*science\b", r"\bdata\s*analyst\b",
        r"\bfp&a\b", r"\bfinance\b", r"\baccounting\b", r"\bsocial\s*media\b", r"\brecruiting\b",
        r"\brecruiter\b", r"\btalent\b", r"\bdeal\s*desk\b", r"\bsales\s*(director|manager|lead|rep)\b",
        r"\brevenue\b", r"\brevops\b", r"\baccount\s*executive\b", r"\bcustomer\s*success\b",
        r"\bcustomer\s*advocacy\b", r"\brenewals\b", r"\bproduct\s*manager\b",
        r"\bengineering\s*manager\b", r"\bsolutions?\s*architect\b", r"\bsecurity\s*engineer\b",
        r"\bpublic\s*sector\b", r"\bcommercial\b", r"\bit\s*project\s*manager\b"
    ]

    # Technical Skills Keywords & Labels (Strictly HSE-Contextualized)
    SKILL_MAP = {
        "ISO 14001 / ISO 45001": [r"\biso\s*14001\b", r"\biso\s*45001\b", r"\bohsas\s*18001\b", r"\bhse\s*management\s*systems?\b"],
        "HSE Governance & Assurance": [r"\b(hse|ehs|she|safety)\s*governance\b", r"\b(hse|ehs|safety)\s*assurance\b", r"\b(statutory|regulatory|safety)\s*compliance\b", r"\bsafety\s*framework\b"],
        "Incident Investigation & RCA": [r"\bincident\s*investigation\b", r"\broot\s*cause\s*(analysis|rca)\b", r"\bfive\s*whys\b", r"\bcapa\b", r"\baccident\s*investigation\b"],
        "Risk Assessment & Management": [r"\bhazop\b", r"\bhira\b", r"\bjha\b", r"\bjob\s*safety\s*analysis\b", r"\bprocess\s*safety\b", r"\b(safety|hse)\s*risk\s*assessment\b"],
        "Contractor Safety Management": [r"\bcontractor\s*safety\b", r"\bpermit\s*to\s*work\b", r"\bptw\b", r"\bcontractor\s*ehs\b"],
        "HSE Audits & Statutory Compliance": [r"\bhse\s*audits?\b", r"\bsafety\s*audits?\b", r"\bohs\s*statutory\b", r"\bepa\s*compliance\b", r"\bosha\b"],
        "Sustainability & ESG": [r"\bsustainability\s*(and|&)\s*hse\b", r"\besg\s*reporting\b", r"\bcarbon\s*neutrality\b", r"\bscope\s*[123]\b", r"\bgreenhouse\s*gas\b"],
        "Safety Culture & Employee Wellness": [r"\bsafety\s*culture\b", r"\bbehavior(al)?\s*safety\b", r"\bbbs\b", r"\bzero\s*harm\b", r"\boccupational\s*wellbeing\b"],
        "HSE Analytics & KPIs": [r"\bltif\b", r"\btrir\b", r"\bltifr\b", r"\blost\s*time\s*injur(y|ies)\b", r"\btotal\s*recordable\b", r"\bsafety\s*kpis?\b"],
        "APAC / Multi-site Leadership": [r"\bmulti-site\s*(safety|hse|ehs|plants?)\b", r"\bplants?\b", r"\bapac\s*(hse|ehs|safety|regional)\b", r"\bglobal\s*(hse|she|ehs|safety)\b"]
    }

    # Qualification Keywords
    QUAL_MAP = {
        "M.Tech / Master's in Environmental Engineering": [r"\bm\.?tech\b", r"\bmaster'?s\b", r"\benvironmental engineering\b", r"\bpost graduate\b"],
        "B.Tech / Bachelor's in Mechanical Engineering": [r"\bb\.?tech\b", r"\bbachelor'?s\b", r"\bmechanical\b", r"\bengineering degree\b"],
        "Diploma in Industrial Safety": [r"\bindustrial safety\b", r"\bnebosh\b", r"\bdiploma in safety\b", r"\bcsp\b", r"\bidosh\b", r"\bdis\b"],
        "Auditor / Lead Auditor Credentials": [r"\blead\s*auditor\b", r"\biso\s*auditor\b", r"\bauditor\b", r"\birqs\b", r"\blrqa\b"]
    }

    # Industry Keywords
    INDUSTRY_MAP = {
        "Manufacturing / Industrial": [r"\bmanufacturing\b", r"\bplants?\b", r"\bfactory\b", r"\bheavy industry\b", r"\boperations\b"],
        "Chemicals / Materials / Nutrition": [r"\bchemical\b", r"\bmaterials?\b", r"\bnutrition\b", r"\bscience\b", r"\bpharma\b", r"\bflavour\b"],
        "Multinational Matrix Environment": [r"\bmultinational\b", r"\bmnc\b", r"\bmatrix\b", r"\bcross-functional\b", r"\bcorporate\b"]
    }

    # Visa & Sponsorship Detection
    SPONSORSHIP_POSITIVE = [
        r"\bvisa sponsorship (?:is )?(?:available|provided|offered)\b",
        r"\bwill sponsor (?:your |a |the )?(?:work |employment )?visa\b"
    ]
    SPONSORSHIP_NEGATIVE = [
        r"\bno (?:visa |work visa )?sponsorship\b", r"\bmust have right to work\b",
        r"\bsponsorship is not available\b", r"\bdo not (?:offer|provide) (?:work )?visa sponsorship\b",
        r"\bapplicants must be legally authorized\b", r"\bcitizens or permanent residents only\b"
    ]

    def is_excluded(self, title: str, description: str, employment_type: str) -> Tuple[bool, str]:
        """Check if job should be excluded as non-leadership, junior, or freelance."""
        full_text = f"{title} {description[:500]} {employment_type}".lower()

        if re.search(r"\b(freelance|intern|internship)\b", f"{title} {employment_type}".lower()):
            return True, "Excluded: Freelance/Internship"
        if "contract" in employment_type.lower() and not ("leadership" in full_text or "manager" in full_text):
            return True, "Excluded: Temporary/Contract non-leadership"

        for pattern in self.EXCLUDED_PATTERNS:
            if re.search(pattern, title.lower()):
                if not any(w in title.lower() for w in ["manager", "head", "director", "lead"]):
                    return True, f"Excluded: Junior or officer role matching {pattern}"

        return False, ""

    def classify_occupational_relevance(self, title: str, description: str) -> Tuple[str, bool, str]:
        """
        Classifies a vacancy into 1 of 7 occupational categories using title, responsibilities, and requirements.
        Returns: (category, is_relevant, explanation)
        """
        title_lower = title.lower()
        desc_sample = description[:2500].lower()
        full_text = f"{title_lower}\n{desc_sample}"

        is_core_hse_title = any(re.search(pat, title_lower) for pat in self.HSE_CORE_TITLE_PATTERNS)
        is_non_hse_domain = any(re.search(pat, title_lower) for pat in self.NON_HSE_DOMAINS)

        # 1. Non-HSE Domain Check (Disqualified from HSE leadership)
        non_occupational_safety = any(re.search(p, title_lower) for p in self.NON_OCCUPATIONAL_SAFETY_PATTERNS)
        explicit_hse = re.search(r"\b(?:hse|ehs|hsse|qhse|ohs|whs|hsw)\b|\bhealth\s*(?:,|and|&)\s*safety\b", title_lower)
        if (is_non_hse_domain and not is_core_hse_title) or (non_occupational_safety and not explicit_hse):
            return (
                OccupationalCategory.UNRELATED,
                False,
                "Excluded: Non-HSE domain (Software/IT, Sales, Finance, Revenue, or Corporate Operations)."
            )

        # An incidental policy paragraph or reporting line is not occupational scope.
        # Prefer review of unusual titles over silently recommending unrelated work.
        if not re.search(r"\b(?:hse|ehs|she|hsw|qhse|hsse|whs|ohs|psm|hazop|hira|loss\s+prevention|safety|environment(?:al)?|sustainability|esg)\b", title_lower) and not is_core_hse_title:
            return (OccupationalCategory.UNRELATED, False,
                    "Title does not establish HSE scope; incidental safety wording is insufficient.")

        # 2. Process Safety / Industrial Safety
        process_pats = [
            r"\bprocess\s*safety\b", r"\bpsm\b", r"\bhazop\b", r"\bhira\b",
            r"\bloss\s*prevention\b", r"\bchemical\s*safety\b", r"\bplant\s*safety\b",
            r"\bmachine\s*safety\b", r"\bindustrial\s*safety\b"
        ]
        if any(re.search(p, title_lower) for p in process_pats) or sum(1 for p in process_pats if re.search(p, desc_sample)) >= 2:
            return (
                OccupationalCategory.PROCESS_INDUSTRIAL_SAFETY,
                True,
                "Role focuses on industrial and process safety management (PSM / HAZOP / Machinery)."
            )

        # 3. Environmental Compliance / Environmental Management
        env_pats = [
            r"\benvironment(al)?\s*compliance\b", r"\benvironment(al)?\s*management\b",
            r"\biso\s*14001\b", r"\bpollution\s*control\b", r"\benvironmental\s*engineer\b",
            r"\beffluent\b", r"\bair\s*emissions?\b"
        ]
        if any(re.search(p, title_lower) for p in env_pats) or sum(1 for p in env_pats if re.search(p, desc_sample)) >= 2:
            return (
                OccupationalCategory.ENVIRONMENTAL_COMPLIANCE,
                True,
                "Role focuses on statutory environmental compliance, ISO 14001, and environmental engineering."
            )

        # 4. Sustainability / ESG with HSE Relevance
        esg_pats = [
            r"\bsustainability\s*(and|&)\s*(hse|ehs|safety)\b", r"\besg\s*reporting\b",
            r"\bcarbon\s*neutrality\b", r"\bgreenhouse\s*gas\b"
        ]
        has_esg = any(re.search(p, title_lower) for p in esg_pats) or sum(1 for p in esg_pats if re.search(p, desc_sample)) >= 2
        has_safety = any(re.search(p, full_text) for p in [r"\bsafety\b", r"\bhse\b", r"\behs\b", r"\bhealth\b"])
        if has_esg and has_safety:
            return (
                OccupationalCategory.SUSTAINABILITY_ESG,
                True,
                "Role integrates corporate sustainability/ESG with operational safety governance."
            )

        # 5. Corporate / Workplace Safety
        workplace_pats = [
            r"\bworkplace\s*(health|safety)\b", r"\boccupational\s*(health|safety)\b",
            r"\bbehavior(al)?\s*safety\b", r"\bbbs\b", r"\bergonomics\b", r"\bzero\s*harm\b",
            r"\bemployee\s*wellbeing\b", r"\bhealth\s*and\s*safety\b", r"\bhsw\b"
        ]
        if any(re.search(p, title_lower) for p in workplace_pats) or sum(1 for p in workplace_pats if re.search(p, desc_sample)) >= 2:
            return (
                OccupationalCategory.CORPORATE_WORKPLACE_SAFETY,
                True,
                "Role focuses on workplace health, behavioral safety culture (BBS), and occupational wellbeing."
            )

        # 6. Core HSE Leadership
        if is_core_hse_title or any(re.search(pat, desc_sample) for pat in self.HSE_CORE_TITLE_PATTERNS):
            return (
                OccupationalCategory.HSE_LEADERSHIP,
                True,
                "Role designates executive Health, Safety & Environment leadership."
            )

        # 7. Adjacent but potentially relevant
        adjacent_pats = [
            r"\bfacilit(y|ies)\s*safety\b", r"\boperations\s*risk\b", r"\bemergency\s*response\b"
        ]
        if any(re.search(p, full_text) for p in adjacent_pats):
            return (
                OccupationalCategory.ADJACENT,
                True,
                "Adjacent operational or risk governance role with potential HSE intersection."
            )

        # 8. Unrelated
        return (
            OccupationalCategory.UNRELATED,
            False,
            "Position does not contain Health, Safety or Environmental (HSE) responsibilities."
        )

    def evaluate(
        self,
        title: str,
        location: str,
        country: Optional[str],
        city: Optional[str],
        employment_type: str,
        is_permanent_fulltime: bool,
        description: str,
        weights: Optional[Dict[str, int]] = None,
        profile: Optional[Dict[str, Any]] = None,
        target_countries: Optional[List[str]] = None
    ) -> MatchResult:
        """
        Compute full 100-point explainable match breakdown across 6 documented dimensions:
        - 1. Occupational Relevance: 25 pts (Mandatory gate)
        - 2. Seniority Alignment: 20 pts (Executive & multi-site leadership)
        - 3. HSE Technical Competencies: 25 pts (ISO 14001/45001, RCA, PSM, Audits)
        - 4. Industry Alignment: 10 pts (Manufacturing, chemical, operations)
        - 5. Educational Qualifications: 10 pts (M.Tech Env, B.Tech Mech, Safety Diploma, Lead Auditor)
        - 6. Location Preference: 10 pts (India, Singapore, Europe, Australia)
        """
        title_lower = title.lower()
        desc_lower = description.lower()
        full_lower = f"{title_lower}\n{desc_lower}"

        reasons: List[str] = []
        if profile is None:
            reasons.append("Candidate profile not supplied: this score measures vacancy relevance; no candidate credentials are verified.")
        if weights is not None:
            reasons.append("Component points below describe raw evidence before weighting; the final weighted breakdown determines the total.")
        matching_qualifications: List[str] = []
        matching_experience: List[str] = []
        matching_skills: List[str] = []
        missing_requirements: List[str] = []

        # Step 1: Occupational Relevance Classification (Gate)
        category, is_relevant, category_explanation = self.classify_occupational_relevance(title, description)

        # Step 2: Strict Exclusion for Unrelated Roles
        if not is_relevant or category == OccupationalCategory.UNRELATED:
            capped_score = 12 if "Non-HSE domain" in category_explanation else 15
            reasons.append(f"Occupational Relevance Gate (0/25 pts): {category_explanation}")
            reasons.append("Disqualification Policy: Occupationally unrelated vacancies are hard-capped at Low Match (<= 15%).")
            return MatchResult(
                score=capped_score,
                level="Low Match (Excluded - Unrelated)",
                reasons=reasons,
                matching_qualifications=[],
                matching_experience=[],
                matching_skills=[],
                missing_requirements=["Position lacks genuine Health, Safety, Environment (HSE/EHS) scope."],
                location_suitability="N/A (Disqualified role)",
                sponsorship_status="Not Evaluated",
                occupational_category=category,
                score_breakdown={
                    "occupational_relevance": 0,
                    "seniority": 0,
                    "technical_skills": 0,
                    "industry": 0,
                    "qualifications": 0,
                    "location": 0
                }
            )

        # Score Breakdown Storage
        breakdown: Dict[str, int] = {}

        # 1. Occupational Relevance (Max: 25)
        if category in [OccupationalCategory.HSE_LEADERSHIP, OccupationalCategory.PROCESS_INDUSTRIAL_SAFETY,
                        OccupationalCategory.ENVIRONMENTAL_COMPLIANCE, OccupationalCategory.CORPORATE_WORKPLACE_SAFETY]:
            occ_score = 25
        elif category == OccupationalCategory.SUSTAINABILITY_ESG:
            occ_score = 23
        else: # Adjacent
            occ_score = 12
        breakdown["occupational_relevance"] = occ_score
        reasons.append(f"Occupational Relevance (+{occ_score}/25 pts): {category} - {category_explanation}")

        # 2. Seniority Alignment (Max: 20)
        is_global_regional = any(k in title_lower for k in self.GLOBAL_REGIONAL_TITLES)
        if is_global_regional and any(t in title_lower for t in ["manager", "head", "director", "lead", "vp"]):
            sen_score = 20
            matching_experience.append("Vacancy includes executive/global/regional HSE leadership; compare its scope with confirmed employment history")
            reasons.append(f"Seniority Alignment (+{sen_score}/20 pts): Global/regional executive scope; employment history needs review.")
        elif "senior" in title_lower and any(t in title_lower for t in ["manager", "lead", "director"]):
            sen_score = 17
            matching_experience.append("Vacancy includes senior HSE management responsibilities")
            reasons.append(f"Seniority Alignment (+{sen_score}/20 pts): Senior HSE Management level.")
        elif any(t in title_lower for t in ["manager", "lead", "head", "director"]):
            sen_score = 14
            matching_experience.append("HSE Management position providing operational safety leadership")
            reasons.append(f"Seniority Alignment (+{sen_score}/20 pts): HSE Management tier.")
        else:
            sen_score = 10
            matching_experience.append("Vacancy includes functional HSE responsibilities; candidate scope needs review")
            reasons.append(f"Seniority Alignment (+{sen_score}/20 pts): Functional safety position.")
        if profile is not None:
            roles = " ".join([profile.get("current_role") or ""] + [r.get("role", "") for r in profile.get("employment_history", []) if isinstance(r, dict)]).lower()
            leadership = any(re.search(p, roles) for p in self.HSE_CORE_TITLE_PATTERNS) and any(w in roles for w in ["manager", "lead", "head", "director"])
            if not leadership:
                sen_score = min(sen_score, 8)
                missing_requirements.append("Confirmed HSE management/leadership role evidence needs review.")
            required_years = re.search(r"\b(\d{1,2})\+?\s*(?:years|yrs)\b", desc_lower)
            if required_years and (profile.get("experience_years") or 0) < int(required_years.group(1)):
                sen_score = min(sen_score, 5)
                missing_requirements.append("Advertised experience exceeds confirmed total industrial experience.")
            reasons.append(f"Profile-based seniority credit: {sen_score}/20. Total industrial years are not treated as years of HSE leadership.")
        breakdown["seniority"] = sen_score

        # 3. Verified HSE Technical Competencies (Max: 25)
        matched_skills_count = 0
        for skill_name, patterns in self.SKILL_MAP.items():
            matched = False
            for pat in patterns:
                if re.search(pat, full_lower):
                    matched = True
                    break
            if matched:
                candidate_text = json.dumps({k: profile.get(k) for k in ("skills", "employment_history", "summary", "achievements")}, ensure_ascii=False).lower() if profile is not None else ""
                evidenced = profile is None or any(re.search(p, candidate_text) for p in patterns)
                if evidenced:
                    matched_skills_count += 1
                    matching_skills.append(skill_name)
                else:
                    missing_requirements.append(f"Candidate evidence needed: {skill_name}")
            else:
                if skill_name in ["ISO 14001 / ISO 45001", "Incident Investigation & RCA", "Risk Assessment & Management"]:
                    missing_requirements.append(f"Explicit mention of {skill_name}")

        skills_ratio = min(1.0, (matched_skills_count / 6.0))
        skills_score = int(25 * skills_ratio)
        breakdown["technical_skills"] = skills_score
        reasons.append(f"Technical Competencies (+{skills_score}/25 pts): {matched_skills_count} vacancy/profile competency overlaps identified ({', '.join(matching_skills[:3])}...).")

        # 4. Industry Alignment (Max: 10)
        matched_ind_count = 0
        industry_evidence = json.dumps({k: profile.get(k) for k in ("employment_history", "summary", "skills", "achievements")}).lower() if profile is not None else ""
        for ind_name, patterns in self.INDUSTRY_MAP.items():
            if any(re.search(pat, full_lower) for pat in patterns):
                if profile is None or any(re.search(pat, industry_evidence) for pat in patterns):
                    matched_ind_count += 1
                else:
                    missing_requirements.append("Candidate industry evidence needed: " + ind_name)

        if matched_ind_count >= 2:
            ind_score = 10
            reasons.append(f"Industry Alignment (+{ind_score}/10 pts): High match with manufacturing, chemical, and multi-plant environments.")
        elif matched_ind_count == 1:
            ind_score = 7
            reasons.append(f"Industry Alignment (+{ind_score}/10 pts): General multinational matrix corporate environment.")
        else:
            ind_score = 3 if profile is None else 0
            reasons.append(f"Industry Alignment (+{ind_score}/10 pts): No confirmed industry overlap supplied; review required.")
        breakdown["industry"] = ind_score

        # Qualifications must be supported by the candidate, not just JD keywords.
        academic = " ".join(profile.get("qualifications", [])).lower() if profile else ""
        credentials = " ".join(profile.get("certifications", [])).lower() if profile else ""
        evidenced_quals = []
        for name, patterns in self.QUAL_MAP.items():
            if not any(re.search(p, full_lower) for p in patterns): continue
            candidate = credentials if "Auditor" in name else academic
            # A different engineering degree is not evidence of a specific discipline.
            if "Environmental" in name:
                present = "environmental engineering" in candidate and "environmental engineering" in full_lower
            elif "Mechanical" in name:
                present = "mechanical engineering" in candidate and "mechanical engineering" in full_lower
            elif "Industrial Safety" in name:
                present = bool(re.search(r"diploma(?: in)? industrial safety|diploma in safety", candidate)) and bool(re.search(r"industrial safety|diploma in safety", full_lower))
            else:
                present = bool(re.search(r"\b(?:lead auditor|certified auditor|auditor training)\b", candidate))
            if present:
                evidenced_quals.append(name)
                matching_qualifications.append(name + " — profile evidence; exact employer requirement needs review")
            else:
                missing_requirements.append("Candidate qualification evidence needed: " + name)
        qual_score = min(10, len(evidenced_quals) * 5)
        breakdown["qualifications"] = qual_score
        reasons.append(f"Education & Credentials (+{qual_score}/10 pts): {len(evidenced_quals)} relevant profile evidence categories. No license, degree equivalence or auditor certification is inferred from the vacancy.")

        # 6. Location Preference (Max: 10)
        configured_countries = target_countries if target_countries is not None else (profile.get("target_countries") if profile is not None else None)
        target_tier1 = configured_countries if configured_countries is not None else ["India", "Singapore"]
        target_tier2 = [] if configured_countries is not None else ["Germany", "Netherlands", "Ireland", "Australia"]
        target_tier3 = ["United Kingdom", "Switzerland", "France", "Sweden"]
        c_norm = (country or "").strip()

        if c_norm in target_tier1:
            loc_score = 10
            loc_suit = f"Optimal Target Location: {c_norm} (Domestic / APAC Hub)"
            reasons.append(f"Location Preference (+{loc_score}/10 pts): Primary target geography ({c_norm}).")
        elif c_norm in target_tier2:
            loc_score = 10
            loc_suit = f"Target International Location: {c_norm} (High Priority)"
            reasons.append(f"Location Preference (+{loc_score}/10 pts): High-priority international destination ({c_norm}).")
        elif c_norm in target_tier3:
            loc_score = 8
            loc_suit = f"Secondary International Location: {c_norm}"
            reasons.append(f"Location Preference (+{loc_score}/10 pts): Secondary European opportunity ({c_norm}).")
        elif "remote" in location.lower() or "remote" in title_lower:
            loc_score = 8
            loc_suit = "Remote / Flexible Work Arrangement"
            reasons.append(f"Location Preference (+{loc_score}/10 pts): Remote work option provided.")
        elif c_norm == "Unknown" or not c_norm:
            loc_score = 3
            loc_suit = "Location not confirmed (labeled Unknown)"
            reasons.append(f"Location Preference (+{loc_score}/10 pts): Location missing or unverified (Unknown).")
        else:
            loc_score = 2
            loc_suit = f"Non-primary location: {c_norm}"
            reasons.append(f"Location Preference (+{loc_score}/10 pts): Non-primary country ({c_norm}).")
        breakdown["location"] = loc_score

        # Step 3: Sponsorship & Work Authorization Detection (Negative Checked First)
        sponsorship_status = "Unknown"
        for pat in self.SPONSORSHIP_NEGATIVE:
            if re.search(pat, full_lower):
                sponsorship_status = "Not Supported"
                reasons.append("Work Authorization: Job posting explicitly requires local work authorization or specifies no visa sponsorship.")
                break
        if sponsorship_status == "Unknown":
            for pat in self.SPONSORSHIP_POSITIVE:
                if re.search(pat, full_lower):
                    sponsorship_status = "Confirmed"
                    reasons.append("Work Authorization: Job posting explicitly states visa sponsorship. Personal eligibility still requires review.")
                    break
        if sponsorship_status == "Unknown":
            reasons.append("Work Authorization: Sponsorship status is Unknown (requires employer confirmation; never assumed confirmed).")

        # Step 4: Calculate Total Score
        if weights is None:
            total_score = sum(breakdown.values())
        else:
            components = {
                "experience_seniority": ("seniority", sen_score / 20),
                "hse_technical_skills": ("technical_skills", skills_score / 25),
                "qualifications": ("qualifications", qual_score / 10),
                "industry_relevance": ("industry", ind_score / 10),
                "location_international": ("location", loc_score / 10),
                "employment_preferences": ("employment", 1.0 if is_permanent_fulltime else 0.0),
            }
            supplied = {k: float(weights.get(k, 0)) for k in components}
            if any(v < 0 or v > 100 for v in supplied.values()) or sum(supplied.values()) <= 0:
                raise ValueError("Scoring weights must be nonnegative with a positive total.")
            # Keep occupational gating/25-point relevance independent of user tuning.
            weighted = {name: 75 * supplied[key] / sum(supplied.values()) * ratio
                        for key, (name, ratio) in components.items()}
            breakdown = {"occupational_relevance": occ_score, **{k: round(v, 4) for k, v in weighted.items()}}
            total_score = occ_score + sum(weighted.values())
            reasons.append("Configured weights distribute the 75 fit points after the independent occupational gate. Weighted breakdown: " + json.dumps(breakdown, sort_keys=True))
        total_score = max(0, min(100, round(total_score)))

        # Step 5: Configurable Match Level Thresholds
        if total_score >= 85:
            level = "Strong Match"
        elif total_score >= 70:
            level = "Good Match"
        elif total_score >= 50:
            level = "Review Manually"
        else:
            level = "Low Match"

        return MatchResult(
            score=total_score,
            level=level,
            reasons=reasons,
            matching_qualifications=matching_qualifications,
            matching_experience=matching_experience,
            matching_skills=matching_skills,
            missing_requirements=missing_requirements,
            location_suitability=loc_suit,
            sponsorship_status=sponsorship_status,
            occupational_category=category,
            score_breakdown=breakdown
        )
