"""Shared profile/preferences input for deterministic scores and cache identity."""
import json
from sqlalchemy.orm import object_session
from backend.app.models import Job, UserProfile, SearchPreference

POLICY_VERSION = "profile-matching-v2"
LIST_FIELDS = ("employment_history", "qualifications", "skills", "certifications", "achievements", "target_countries", "target_titles")


def profile_data(profile):
    if profile is None: return None
    data = {name: getattr(profile, name, None) for name in ("name", "current_role", "current_company", "location", "experience_years", "summary", "cv_id", "consent_given_for_ai")}
    for name in LIST_FIELDS:
        value = getattr(profile, name, None)
        try: data[name] = json.loads(value or "[]") if isinstance(value, (str, type(None))) else value
        except (ValueError, TypeError): data[name] = []
    return data


def match_options(profile, db=None):
    db = db or (object_session(profile) if profile is not None else None)
    pref = db.query(SearchPreference).first() if db is not None else None
    return dict(profile=profile_data(profile), weights=json.loads(pref.scoring_weights) if pref else None,
                target_countries=json.loads(pref.target_countries) if pref else None)


def evaluate_job(job, profile, db=None):
    from .matcher import HSEJobMatcher
    return HSEJobMatcher().evaluate(title=job.title, location=job.location or "", country=job.country,
        city=job.city, employment_type=job.employment_type or "Unknown",
        is_permanent_fulltime=bool(job.is_permanent_fulltime), description=job.description or "",
        **match_options(profile, db))


def refresh_job_scores(db):
    profile = db.query(UserProfile).first()
    for job in db.query(Job).all():
        result = evaluate_job(job, profile, db)
        apply_score(job, result)


def apply_score(job, result):
    job.match_score = result.score
    job.match_level = result.level
    for field in ("match_reasons", "matching_qualifications", "matching_experience", "matching_skills", "missing_requirements"):
        value = result.reasons if field == "match_reasons" else getattr(result, field)
        setattr(job, field, json.dumps(value))
    job.location_suitability = result.location_suitability
    job.sponsorship_status = result.sponsorship_status
