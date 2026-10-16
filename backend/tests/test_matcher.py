import pytest
from backend.services.matcher import HSEJobMatcher

def test_matcher_leadership_high_score():
    matcher = HSEJobMatcher()
    title = "Global EHS Manager - APAC & EMEA"
    description = """
    We are seeking an experienced Global EHS Manager to lead workplace health, safety and environmental assurance across 15+ manufacturing plants.
    Key responsibilities:
    - Oversee ISO 14001 and ISO 45001 management systems and statutory compliance.
    - Direct incident investigation and root cause analysis (RCA).
    - Manage contractor safety management and risk assessment protocols.
    - Lead sustainability, carbon reduction, and ESG reporting initiatives.
    - Drive proactive safety culture and employee wellness programs.
    - Establish HSE performance reporting and KPIs.
    Qualifications:
    - Master's or Bachelor's in Environmental Engineering, Mechanical Engineering, or related technical discipline.
    - Diploma in Industrial Safety or NEBOSH certification.
    - 15+ years of multinational corporate HSE leadership experience.
    Visa sponsorship available for qualifying international candidates.
    """
    
    result = matcher.evaluate(
        title=title,
        location="Amsterdam, Netherlands",
        country="Netherlands",
        city="Amsterdam",
        employment_type="Permanent Full-time",
        is_permanent_fulltime=True,
        description=description
    )

    assert result.score >= 85
    assert result.level == "Excellent Match"
    assert "ISO 14001 / ISO 45001" in result.matching_skills
    assert "Incident Investigation & RCA" in result.matching_skills
    assert result.sponsorship_status == "Confirmed"
    assert "Netherlands" in result.location_suitability

def test_matcher_excludes_junior_officer_and_intern():
    matcher = HSEJobMatcher()
    
    is_excl, reason = matcher.is_excluded("Junior Safety Officer", "Entry level position for basic monitoring", "Full-time")
    assert is_excl is True
    assert "Junior or officer" in reason

    is_excl2, reason2 = matcher.is_excluded("EHS Intern", "Summer internship program", "Temporary")
    assert is_excl2 is True

    is_excl3, reason3 = matcher.is_excluded("Regional HSE Director", "Leading safety across plants", "Permanent")
    assert is_excl3 is False

def test_matcher_location_scoring():
    matcher = HSEJobMatcher()
    
    # Target Country (India)
    res_india = matcher.evaluate(
        title="Regional HSE Manager",
        location="Hyderabad, India",
        country="India",
        city="Hyderabad",
        employment_type="Full-time",
        is_permanent_fulltime=True,
        description="Lead regional safety management."
    )
    assert res_india.score >= 55

    # Secondary / Non-target country
    res_us = matcher.evaluate(
        title="Regional HSE Manager",
        location="Dallas, Texas",
        country="United States",
        city="Dallas",
        employment_type="Full-time",
        is_permanent_fulltime=True,
        description="Lead regional safety management."
    )
    assert res_india.score > res_us.score

def test_matcher_sponsorship_detection():
    matcher = HSEJobMatcher()
    
    res_neg = matcher.evaluate(
        title="Senior EHS Manager",
        location="Sydney, Australia",
        country="Australia",
        city="Sydney",
        employment_type="Full-time",
        is_permanent_fulltime=True,
        description="Candidates must have right to work in Australia. No visa sponsorship available."
    )
    assert res_neg.sponsorship_status == "Not Supported"

def test_matcher_strictly_disqualifies_non_hse_roles():
    matcher = HSEJobMatcher()

    # Stripe Engineering Manager case
    res_stripe = matcher.evaluate(
        title="Engineering Manager, Forward Deployed (Privy)",
        location="NYC-Privy",
        country="United States",
        city="New York",
        employment_type="Full-time",
        is_permanent_fulltime=True,
        description="Lead a software engineering team building developer tools and APIs."
    )
    assert res_stripe.score <= 15
    assert res_stripe.level == "Low Match"
    assert any("Domain Disqualification" in r for r in res_stripe.reasons)

    # General Tech / Sales roles
    for non_hse_title in ["Senior Software Engineer", "Sales Development Representative", "Deal Desk Manager", "Frontend Lead"]:
        res = matcher.evaluate(
            title=non_hse_title,
            location="Singapore",
            country="Singapore",
            city="Singapore",
            employment_type="Full-time",
            is_permanent_fulltime=True,
            description="Manage client accounts and revenue pipeline."
        )
        assert res.score <= 15
        assert res.level == "Low Match"

def test_matcher_scores_genuine_hse_role_high():
    matcher = HSEJobMatcher()

    res = matcher.evaluate(
        title="Global Head of SHE (Safety, Health & Environment)",
        location="Singapore / Hyderabad, India",
        country="Singapore",
        city="Singapore",
        employment_type="Full-time",
        is_permanent_fulltime=True,
        description="""Direct global SHE governance across 19 manufacturing plants.
        Lead ISO 14001 and ISO 45001 management systems, incident investigation with RCA,
        contractor safety management, behavior-based safety culture (BBS), and ESG reporting."""
    )
    assert res.score >= 85
    assert res.level == "Excellent Match"
    assert "ISO 14001 / ISO 45001" in res.matching_skills
    assert "Incident Investigation & RCA" in res.matching_skills
