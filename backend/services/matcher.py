import re
from typing import Dict, List, Any, Optional, Tuple

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
        sponsorship_status: str
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
            "sponsorship_status": self.sponsorship_status
        }

class HSEJobMatcher:
    """
    Local, rules-based matching engine for Raghunath Reddy's HSE leadership profile.
    Total score: 100 points.
    - Experience & Seniority: 25 pts
    - HSE Technical Skills: 25 pts
    - Educational Qualifications: 15 pts
    - Industry Relevance: 15 pts
    - Location & International Eligibility: 15 pts
    - Employment Preferences: 5 pts
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
        r"\bhse\b", r"\behs\b", r"\bshe\b", r"\bshe&s\b", r"\bhsw\b", r"\bqhse\b",
        r"\bhealth\s*(and|&)\s*safety\b", r"\bworkplace\s*health\b", r"\bworkplace\s*safety\b",
        r"\boccupational\s*health\b", r"\boccupational\s*safety\b", r"\benvironment(al)?\s*health\b",
        r"\bsafety\s*(and|&)\s*environment\b", r"\bprocess\s*safety\b", r"\bindustrial\s*safety\b",
        r"\bsafety\s*manager\b", r"\bsafety\s*director\b", r"\bsafety\s*lead\b", r"\bhead\s*of\s*safety\b",
        r"\bsustainability\s*(and|&)\s*safety\b", r"\benvironmental\s*manager\b",
        r"\bsafety\s*assurance\b", r"\bsafety\s*governance\b", r"\behs\s*manager\b", r"\bhse\s*manager\b"
    ]

    # Explicit Non-HSE Domain Titles (Strictly Disqualified from High HSE Matches)
    NON_HSE_DOMAINS = [
        r"\bsoftware\b", r"\bfrontend\b", r"\bbackend\b", r"\bfull\s*stack\b", r"\bdevops\b",
        r"\bcloud\b", r"\bdata\s*engineer\b", r"\bdata\s*science\b", r"\bdata\s*analyst\b",
        r"\bfp&a\b", r"\bfinance\b", r"\baccounting\b", r"\bsocial\s*media\b", r"\brecruiting\b",
        r"\brecruiter\b", r"\btalent\b", r"\bdeal\s*desk\b", r"\bsales\s*(director|manager|lead|rep)\b",
        r"\brevenue\b", r"\brevops\b", r"\baccount\s*executive\b", r"\bcustomer\s*success\b",
        r"\bcustomer\s*advocacy\b", r"\brenewals\b", r"\bproduct\s*manager\b",
        r"\bengineering\s*manager\b", r"\bsolutions?\s*architect\b", r"\bsecurity\s*engineer\b",
        r"\bpublic\s*sector\b", r"\bcommercial\b"
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
        "MBA / Business Leadership": [r"\bmba\b", r"\bhuman resources\b", r"\bbusiness administration\b", r"\bmanagement degree\b"],
        "Diploma in Industrial Safety": [r"\bindustrial safety\b", r"\bnebosh\b", r"\bdiploma in safety\b", r"\bcsp\b", r"\bidosh\b", r"\bdis\b"]
    }

    # Industry Keywords
    INDUSTRY_MAP = {
        "Manufacturing / Industrial": [r"\bmanufacturing\b", r"\bplants?\b", r"\bfactory\b", r"\bheavy industry\b", r"\boperations\b"],
        "Chemicals / Materials / Nutrition": [r"\bchemical\b", r"\bmaterials?\b", r"\bnutrition\b", r"\bscience\b", r"\bpharma\b", r"\bflavour\b"],
        "Multinational Matrix Environment": [r"\bmultinational\b", r"\bmnc\b", r"\bmatrix\b", r"\bcross-functional\b", r"\bcorporate\b"]
    }

    # Visa & Sponsorship Detection
    SPONSORSHIP_POSITIVE = [
        r"\bvisa sponsorship available\b", r"\bwill sponsor\b", r"\brelocation assistance provided\b",
        r"\brelocation package\b", r"\bglobal applicants welcome\b", r"\bassistance with visa\b"
    ]
    SPONSORSHIP_NEGATIVE = [
        r"\bno visa sponsorship\b", r"\bmust have right to work\b", r"\bno relocation\b",
        r"\bapplicants must be legally authorized\b", r"\bcitizens or permanent residents only\b"
    ]

    def is_excluded(self, title: str, description: str, employment_type: str) -> Tuple[bool, str]:
        """Check if job should be excluded as non-leadership, junior, or freelance."""
        full_text = f"{title} {description[:500]} {employment_type}".lower()

        # Check employment type
        if "freelance" in full_text or "intern" in full_text:
            return True, "Excluded: Freelance/Internship"
        if "contract" in employment_type.lower() and not ("leadership" in full_text or "manager" in full_text):
            return True, "Excluded: Temporary/Contract non-leadership"

        for pattern in self.EXCLUDED_PATTERNS:
            if re.search(pattern, title.lower()):
                # Only exclude if not also high-level manager
                if not any(w in title.lower() for w in ["manager", "head", "director", "lead"]):
                    return True, f"Excluded: Junior or officer role matching {pattern}"

        return False, ""

    def evaluate(
        self,
        title: str,
        location: str,
        country: Optional[str],
        city: Optional[str],
        employment_type: str,
        is_permanent_fulltime: bool,
        description: str,
        weights: Optional[Dict[str, int]] = None
    ) -> MatchResult:
        """
        Compute full 100-point match breakdown.
        """
        weights = weights or {
            "experience_seniority": 25,
            "hse_technical_skills": 25,
            "qualifications": 15,
            "industry_relevance": 15,
            "location_international": 15,
            "employment_preferences": 5
        }

        title_lower = title.lower()
        desc_lower = description.lower()
        full_lower = f"{title_lower}\n{desc_lower}"

        reasons: List[str] = []
        matching_qualifications: List[str] = []
        matching_experience: List[str] = []
        matching_skills: List[str] = []
        missing_requirements: List[str] = []

        # Check HSE Domain Relevance
        is_core_hse_title = any(re.search(pat, title_lower) for pat in self.HSE_CORE_TITLE_PATTERNS)
        is_non_hse_domain = any(re.search(pat, title_lower) for pat in self.NON_HSE_DOMAINS)
        core_hse_desc_count = sum(1 for pat in self.HSE_CORE_TITLE_PATTERNS if re.search(pat, desc_lower))

        # 0. Strict Domain Gate
        # If title is explicitly non-HSE (Software, Sales, Finance, Devops, etc.) and lacks core HSE title:
        if is_non_hse_domain and not is_core_hse_title:
            return MatchResult(
                score=12,
                level="Low Match",
                reasons=["Domain Disqualification: Role belongs to non-HSE domain (Software, Sales, Finance, Revenue, or Corporate Operations)."],
                matching_qualifications=[],
                matching_experience=[],
                matching_skills=[],
                missing_requirements=["Health, Safety & Environment (HSE/EHS) leadership domain scope is absent."],
                location_suitability="N/A (Disqualified domain)",
                sponsorship_status="Not Evaluated"
            )

        # If role has zero HSE keywords in both title and description:
        if not is_core_hse_title and core_hse_desc_count == 0:
            return MatchResult(
                score=15,
                level="Low Match",
                reasons=["Domain Warning: Position does not contain Health, Safety or Environmental (HSE) responsibilities."],
                matching_qualifications=[],
                matching_experience=[],
                matching_skills=[],
                missing_requirements=["No explicit Health, Safety & Environment (HSE/EHS) scope identified in title or job description."],
                location_suitability="N/A (Non-HSE role)",
                sponsorship_status="Not Evaluated"
            )

        # 1. Experience & Seniority (Max: 25)
        w_exp = weights.get("experience_seniority", 25)
        exp_score = 0
        is_global_regional = any(k in title_lower for k in self.GLOBAL_REGIONAL_TITLES)

        if is_core_hse_title:
            if is_global_regional and ("manager" in title_lower or "head" in title_lower or "director" in title_lower or "lead" in title_lower):
                exp_score = w_exp
                matching_experience.append("Executive/Global/Regional HSE Leadership role directly matches your 18+ years APAC & Global background")
                reasons.append(f"Seniority (+{exp_score}): Executive/Global HSE Leadership scope.")
            elif "senior" in title_lower and ("manager" in title_lower or "lead" in title_lower or "director" in title_lower):
                exp_score = int(w_exp * 0.92)
                matching_experience.append("Senior HSE Manager / Lead role matching your extensive management record")
                reasons.append(f"Seniority (+{exp_score}): Senior HSE Management level.")
            elif "manager" in title_lower or "lead" in title_lower or "head" in title_lower or "director" in title_lower:
                exp_score = int(w_exp * 0.84)
                matching_experience.append("HSE Manager position providing direct operational leadership")
                reasons.append(f"Seniority (+{exp_score}): HSE Management position.")
            else:
                exp_score = int(w_exp * 0.65)
                matching_experience.append("Core HSE function alignable with leadership scope")
                reasons.append(f"Seniority (+{exp_score}): HSE functional match.")
        else:
            exp_score = int(w_exp * 0.20)
            missing_requirements.append("Job title does not clearly designate an HSE leadership tier")

        # 2. HSE Technical Skills (Max: 25)
        w_skills = weights.get("hse_technical_skills", 25)
        matched_skills_count = 0
        total_skills_count = len(self.SKILL_MAP)

        for skill_name, patterns in self.SKILL_MAP.items():
            matched = False
            for pat in patterns:
                if re.search(pat, full_lower):
                    matched = True
                    break
            if matched:
                matched_skills_count += 1
                matching_skills.append(skill_name)
            else:
                if skill_name in ["ISO 14001 / ISO 45001", "Incident Investigation & RCA", "Risk Assessment & Management"]:
                    missing_requirements.append(f"Explicit mention of {skill_name}")

        skills_ratio = min(1.0, (matched_skills_count / 6.0))  # 6 key skills gives full score
        skills_score = int(w_skills * skills_ratio)
        reasons.append(f"Technical Skills (+{skills_score}): {matched_skills_count} core competencies identified (ISO standards, incident investigation, audits, governance).")

        # 3. Educational Qualifications (Max: 15)
        w_qual = weights.get("qualifications", 15)
        matched_quals_count = 0

        for qual_name, patterns in self.QUAL_MAP.items():
            matched = False
            for pat in patterns:
                if re.search(pat, full_lower):
                    matched = True
                    break
            if matched:
                matched_quals_count += 1
                matching_qualifications.append(qual_name)

        if matched_quals_count >= 2:
            qual_score = w_qual
            reasons.append(f"Qualifications (+{qual_score}): Strong match with your M.Tech, B.Tech Engineering, MBA, and Safety certifications.")
        elif matched_quals_count == 1:
            qual_score = int(w_qual * 0.75)
            reasons.append(f"Qualifications (+{qual_score}): Key educational requirements satisfied.")
        else:
            # Baseline qualification points if general degree required
            if "degree" in full_lower or "bachelor" in full_lower or "master" in full_lower:
                qual_score = int(w_qual * 0.60)
                matching_qualifications.append("General Engineering / Technical Degree requirement met")
                reasons.append(f"Qualifications (+{qual_score}): General higher degree requirement met by your M.Tech/B.Tech.")
            else:
                qual_score = int(w_qual * 0.40)

        # 4. Industry Relevance (Max: 15)
        w_ind = weights.get("industry_relevance", 15)
        matched_ind_count = 0
        for ind_name, patterns in self.INDUSTRY_MAP.items():
            for pat in patterns:
                if re.search(pat, full_lower):
                    matched_ind_count += 1
                    break

        if matched_ind_count >= 2:
            ind_score = w_ind
            reasons.append(f"Industry (+{ind_score}): Highly aligned with manufacturing, chemical, multi-plant operations.")
        elif matched_ind_count == 1:
            ind_score = int(w_ind * 0.70)
            reasons.append(f"Industry (+{ind_score}): Aligns with corporate multinational environment.")
        else:
            ind_score = int(w_ind * 0.40)

        # 5. Location and International Eligibility (Max: 15)
        w_loc = weights.get("location_international", 15)
        loc_score = 0
        loc_suit = "Unknown"

        target_tier1 = ["India", "Singapore"]
        target_tier2 = ["Germany", "Netherlands", "Ireland", "Australia"]
        target_tier3 = ["United Kingdom", "Switzerland", "France", "Sweden"]

        c_norm = (country or "").strip()

        if c_norm in target_tier1:
            loc_score = w_loc
            loc_suit = f"Optimal Location: {c_norm} (Domestic / APAC Hub)"
            reasons.append(f"Location (+{loc_score}): Primary target geography ({c_norm}).")
        elif c_norm in target_tier2:
            loc_score = w_loc
            loc_suit = f"Target International Location: {c_norm} (Europe / Australia priority)"
            reasons.append(f"Location (+{loc_score}): High-priority international destination ({c_norm}).")
        elif c_norm in target_tier3:
            loc_score = int(w_loc * 0.80)
            loc_suit = f"Secondary International Location: {c_norm}"
            reasons.append(f"Location (+{loc_score}): Broader European opportunity ({c_norm}).")
        elif "remote" in location.lower() or "remote" in title_lower:
            loc_score = int(w_loc * 0.90)
            loc_suit = "Remote / Flexible Work Arrangement"
            reasons.append(f"Location (+{loc_score}): Remote flexibility offered.")
        elif c_norm == "Unknown" or not c_norm:
            loc_score = int(w_loc * 0.40)
            loc_suit = "Location not confirmed (labeled Unknown)"
            reasons.append(f"Location (+{loc_score}): Location uncertain, marked Unknown.")
        else:
            loc_score = int(w_loc * 0.20)
            loc_suit = f"Non-primary location: {c_norm}"

        # 6. Employment Preferences (Max: 5)
        w_emp = weights.get("employment_preferences", 5)
        emp_score = 0
        if is_permanent_fulltime:
            emp_score = w_emp
            reasons.append(f"Employment Type (+{emp_score}): Confirmed Permanent Full-time.")
        elif "full-time" in employment_type.lower() or "full time" in employment_type.lower():
            emp_score = int(w_emp * 0.8)
            reasons.append(f"Employment Type (+{emp_score}): Full-time vacancy.")
        elif employment_type == "Unknown":
            emp_score = int(w_emp * 0.3)
            reasons.append("Employment Type (+1): Unverified permanence (Unknown).")
        else:
            emp_score = 0

        # Sponsorship Detection (check negative first so 'no visa sponsorship' is properly flagged)
        sponsorship_status = "Unknown"
        for pat in self.SPONSORSHIP_NEGATIVE:
            if re.search(pat, full_lower):
                sponsorship_status = "Not Supported"
                reasons.append("Sponsorship: Job posting explicitly notes local work authorization required or no visa sponsorship.")
                break
        if sponsorship_status == "Unknown":
            for pat in self.SPONSORSHIP_POSITIVE:
                if re.search(pat, full_lower):
                    sponsorship_status = "Confirmed"
                    reasons.append("Sponsorship: Job posting explicitly indicates visa/relocation support.")
                    break

        # Calculate Total Score
        total_score = exp_score + skills_score + qual_score + ind_score + loc_score + emp_score
        total_score = max(0, min(100, total_score))

        # Match Level Classification
        if total_score >= 85:
            level = "Excellent Match"
        elif total_score >= 75:
            level = "Strong Match"
        elif total_score >= 60:
            level = "Potential Match"
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
            sponsorship_status=sponsorship_status
        )
