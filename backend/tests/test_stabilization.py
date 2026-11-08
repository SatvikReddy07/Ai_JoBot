import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import patch
import httpx
import pytest
from backend.tests.conftest import client
from backend.app.models import Job, UserProfile, EmployerBoard, SearchPreference, ApplicationHistory
from backend.connectors.base import RawJob
from backend.services.discovery import run_discovery_service
from backend.services.gemini_service import analyze_job_with_ai, assessment_cache_key
from backend.services.matcher import HSEJobMatcher

@pytest.fixture
def context(db_session):
    p=db_session.query(UserProfile).first()
    p.name='Synthetic Candidate';p.current_role='Regional EHS Manager';p.current_company='Synthetic Industry'
    p.summary='Manufacturing plant safety and environmental compliance.'
    p.qualifications='["M.Tech Environmental Engineering"]';p.certifications='[]'
    p.skills='["ISO 14001", "ISO 45001", "Incident Investigation", "Root Cause Analysis", "Contractor Safety", "Process Safety", "HSE Governance"]'
    p.employment_history='[{"company":"Synthetic Industry","role":"Regional EHS Manager","highlights":["Manufacturing plant safety"]}]'
    p.achievements='[]';p.target_countries='["India", "Germany"]';p.consent_given_for_ai=False
    db_session.query(EmployerBoard).delete()
    b=EmployerBoard(company_name='Synthetic Employer',platform='greenhouse',board_token='synthetic',is_enabled=True)
    j=Job(source='greenhouse',source_job_id='live-1',company=b.company_name,title='Regional HSE Manager',
        description='Lead HSE governance, ISO 14001 and ISO 45001, process safety, contractor safety, incident investigation and RCA in manufacturing plants. Masters in Environmental Engineering required.',
        location='Berlin, Germany',country='Germany',url='https://boards.greenhouse.io/synthetic/jobs/live-1',
        employment_type='Full-time',is_permanent_fulltime=True,is_active=True,is_saved=True,application_status='Saved',
        last_verified_at=datetime.utcnow()-timedelta(days=3))
    db_session.add_all([b,j]);db_session.commit()
    return p,b,j


def raw(job,**changes):
    data={name:getattr(job,name) for name in ('source','source_job_id','company','title','description','location','city','country','url','employment_type','is_permanent_fulltime','raw_description_html','posted_date')}
    data.update(changes)
    return RawJob(**data)


def refresh(db,b,jobs=None,error=None):
    async def fetch(_):
        if error: raise error
        return jobs
    with patch('backend.services.discovery.GreenhouseConnector.fetch_jobs',fetch):
        return asyncio.run(run_discovery_service(db,b.id))


def evaluate(profile=None,weights=None,description=None,title='Regional EHS Manager'):
    return HSEJobMatcher().evaluate(title=title,location='Berlin, Germany',country='Germany',city='Berlin',
        employment_type='Full-time',is_permanent_fulltime=True,
        description=description or 'ISO 14001 and ISO 45001, process safety, RCA and incident investigation in manufacturing plants. Masters in Environmental Engineering required.',
        profile=profile,weights=weights)


def test_profile_evidence_changes_match_without_inventing_certifications():
    empty={'current_role':'Maintenance Engineer','skills':[],'qualifications':[],'certifications':[],'employment_history':[]}
    strong={**empty,'current_role':'Regional EHS Manager','skills':['ISO 14001','ISO 45001','Process Safety','RCA','Incident Investigation'],
        'qualifications':['M.Tech Environmental Engineering']}
    low=evaluate(empty);high=evaluate(strong)
    assert high.score>low.score
    assert not low.matching_qualifications
    assert not any('certified Lead Auditor requirements' in r for r in high.reasons)
    assert all('Auditor' not in q for q in high.matching_qualifications)


def test_different_degree_does_not_become_matching_qualification():
    result=evaluate({'qualifications':['Master of Law'],'certifications':[]},description='Environmental engineering masters required. Lead HSE governance.')
    assert not result.matching_qualifications


def test_weights_change_score_but_never_bypass_domain_gate():
    qualifications={'qualifications':100}
    skills={'hse_technical_skills':100}
    profile={'skills':['ISO 14001','ISO 45001','Process Safety','Incident Investigation','RCA'],'qualifications':[],'certifications':[]}
    assert evaluate(profile,skills).score>evaluate(profile,qualifications).score
    assert evaluate(profile,skills,title='Senior Software Engineer').score<=15

@pytest.mark.parametrize('values',[{'qualifications':-1},{'qualifications':101},{'qualifications':0,'hse_technical_skills':0,'experience_seniority':0,'industry_relevance':0,'location_international':0,'employment_preferences':0}])
def test_invalid_settings_weights_rejected(values):
    r=client.put('/api/settings',json={'scoring_weights':values})
    assert r.status_code==422


def test_explicit_settings_update_refreshes_existing_scores(db_session,context):
    _,_,j=context
    high={'experience_seniority':0,'hse_technical_skills':100,'qualifications':0,'industry_relevance':0,'location_international':0,'employment_preferences':0}
    assert client.put('/api/settings',json={'scoring_weights':high}).status_code==200
    a=client.get(f'/api/jobs/{j.id}').json()['match_score']
    low={**high,'hse_technical_skills':0,'qualifications':100}
    assert client.put('/api/settings',json={'scoring_weights':low}).status_code==200
    b=client.get(f'/api/jobs/{j.id}').json()['match_score']
    assert a>b


def test_profile_edit_recalculates_without_altering_history(db_session,context):
    _,_,j=context
    before=client.put('/api/profile',json={'skills':['ISO 14001','ISO 45001','Process Safety','RCA','Incident Investigation']})
    assert before.status_code==200
    a=client.get(f'/api/jobs/{j.id}').json()['match_score']
    assert client.put('/api/profile',json={'skills':[],'employment_history':[],'summary':'','qualifications':[],'current_role':'Maintenance Engineer'}).status_code==200
    row=client.get(f'/api/jobs/{j.id}').json()
    assert row['match_score']<a and row['is_saved'] and row['application_status']=='Saved'

@pytest.mark.parametrize('text',['Relocation package provided.','Global applicants welcome.','Relocation assistance provided.','We will sponsor safety awards.'])
def test_relocation_and_generic_sponsor_are_not_visa_evidence(text):
    assert evaluate(description='Lead EHS governance. '+text).sponsorship_status=='Unknown'


def test_no_relocation_does_not_negate_explicit_visa_support():
    assert evaluate(description='Lead EHS governance. No relocation assistance. Visa sponsorship available.').sponsorship_status=='Confirmed'


def test_international_does_not_match_intern_substring():
    excluded,_=HSEJobMatcher().is_excluded('Regional HSE Manager','International manufacturing and internal audits.','Full-time')
    assert not excluded


def test_profile_change_invalidates_cached_fallback_and_hides_old_api_result(db_session,context):
    p,_,j=context
    first=asyncio.run(analyze_job_with_ai(db_session,j,p));old_hash=first.job_hash;old_score=first.match_score
    p.skills='[]';p.summary='';p.employment_history='[]';p.qualifications='[]';p.current_role='Maintenance Engineer';db_session.commit()
    assert client.get(f'/api/jobs/{j.id}/ai-assessment').status_code==404
    assert client.get(f'/api/jobs/{j.id}').json()['ai_assessment'] is None
    second=asyncio.run(analyze_job_with_ai(db_session,j,p))
    assert second.job_hash!=old_hash and second.match_score<old_score
    assert client.get(f'/api/jobs/{j.id}/ai-assessment').status_code==200


def test_model_and_weights_participate_in_cache_identity(db_session,context,monkeypatch):
    p,_,j=context
    original=assessment_cache_key(db_session,j,p)
    monkeypatch.setenv('GEMINI_MODEL','synthetic-model')
    assert assessment_cache_key(db_session,j,p)!=original
    a=assessment_cache_key(db_session,j,p)
    pref=db_session.query(SearchPreference).first();pref.scoring_weights=json.dumps({'hse_technical_skills':100});db_session.commit()
    assert assessment_cache_key(db_session,j,p)!=a


def test_consent_revocation_does_not_reuse_ai_result(db_session,context):
    p,_,j=context
    p.consent_given_for_ai=True;db_session.commit()
    assessment=asyncio.run(analyze_job_with_ai(db_session,j,p));assessment.engine_used='ai';assessment.match_score=99;db_session.commit()
    p.consent_given_for_ai=False;db_session.commit()
    with patch('google.genai.Client') as external:
        result=asyncio.run(analyze_job_with_ai(db_session,j,p))
        external.assert_not_called()
    assert result.engine_used=='rules_fallback'


def test_transient_ai_failure_retries_instead_of_caching_indefinitely(db_session,context,monkeypatch):
    p,_,j=context;p.consent_given_for_ai=True;db_session.commit()
    monkeypatch.setenv('GEMINI_API_KEY','synthetic-not-a-real-key')
    with patch('google.genai.Client',side_effect=RuntimeError('Synthetic offline error')) as external:
        asyncio.run(analyze_job_with_ai(db_session,j,p))
        asyncio.run(analyze_job_with_ai(db_session,j,p))
        assert external.call_count==2


def test_ai_cannot_upgrade_an_unrelated_role(db_session,context,monkeypatch):
    p,_,j=context;p.consent_given_for_ai=True;j.title='Software Engineering Manager';j.description='Build developer APIs';db_session.commit()
    monkeypatch.setenv('GEMINI_API_KEY','synthetic-key')
    with patch('google.genai.Client') as external:
        result=asyncio.run(analyze_job_with_ai(db_session,j,p))
        external.assert_not_called()
    assert result.match_score<=15 and result.application_priority=='Low'


def test_successful_snapshot_inactivates_missing_job_but_preserves_record(db_session,context):
    _,b,j=context
    history=ApplicationHistory(job_id=j.id,previous_status='Discovered',new_status='Saved',notes='Synthetic saved record')
    db_session.add(history);db_session.commit()
    result=refresh(db_session,b,[])
    db_session.refresh(j)
    assert result['jobs_inactivated']==1 and not j.is_active
    assert j.is_saved and j.application_status=='Saved'
    assert db_session.query(ApplicationHistory).count()==1
    assert client.get('/api/jobs').json()['total']==0
    assert client.get('/api/jobs?include_inactive=true').json()['total']==1
    assert client.post('/api/phase4/applications',json={'job_id':j.id}).status_code==409


def test_failed_snapshot_never_inactivates_stored_jobs(db_session,context):
    _,b,j=context
    result=refresh(db_session,b,error=RuntimeError('Synthetic feed failure'))
    db_session.refresh(j)
    assert result['status']=='failed' and j.is_active and j.is_saved


def test_reappearing_job_reactivates_same_saved_record(db_session,context):
    _,b,j=context;j.is_active=False;db_session.commit()
    result=refresh(db_session,b,[raw(j,title='Regional EHS Manager — Updated')])
    db_session.refresh(j)
    assert result['jobs_updated']==1 and j.is_active and j.is_saved
    assert j.title.endswith('Updated') and db_session.query(Job).count()==1


def test_custom_and_ambiguous_board_urls_are_not_inferred_closed(db_session,context):
    _,b,j=context
    j.url='https://synthetic.example.invalid/careers/live-1';db_session.commit()
    refresh(db_session,b,[]);db_session.refresh(j);assert j.is_active
    j.url='https://boards.greenhouse.io/synthetic/jobs/live-1'
    db_session.add(EmployerBoard(company_name=b.company_name,platform=b.platform,board_token='another',is_enabled=True));db_session.commit()
    refresh(db_session,b,[]);db_session.refresh(j);assert j.is_active


def test_partial_database_refresh_is_rolled_back(db_session,context):
    _,b,j=context
    from backend.services.matching_context import apply_score
    def broken(job,result):
        apply_score(job,result)
        raise RuntimeError('Synthetic write-stage failure')
    with patch('backend.services.matching_context.apply_score',broken):
        result=refresh(db_session,b,[raw(j,title='Changed title before error')])
    db_session.refresh(j)
    assert result['status']=='failed' and j.title=='Regional HSE Manager' and j.is_active

@pytest.mark.parametrize('payload,status',[(None,404),({'error':'bad response'},200),({'jobs':[{'id':'bad','title':'HSE Manager'}]},200),({'jobs':[],'meta':{'total':10}},200)])
def test_connector_errors_preserve_jobs_instead_of_becoming_empty_snapshot(db_session,context,payload,status):
    _,b,j=context
    real=httpx.AsyncClient
    transport=httpx.MockTransport(lambda request:httpx.Response(status,json=payload,request=request))
    with patch('backend.connectors.greenhouse.httpx.AsyncClient',side_effect=lambda **kw:real(transport=transport,**kw)):
        result=asyncio.run(run_discovery_service(db_session,b.id))
    db_session.refresh(j)
    assert result['status']=='failed' and j.is_active


def test_api_pagination_includes_last_page_and_inactive_history(db_session,context):
    _,_,j=context
    for n in range(120):
        db_session.add(Job(source='synthetic',source_job_id=str(n),company='Synthetic Employer',title=f'History {n}',location='India',
            description='Synthetic only',url=f'https://synthetic.example.invalid/{n}',employment_type='Full-time',is_active=False,is_saved=True,application_status='Saved'))
    db_session.commit()
    first=client.get('/api/jobs?include_inactive=true&page_size=100&page=1').json()
    last=client.get('/api/jobs?include_inactive=true&page_size=100&page=2').json()
    assert first['total']==121 and last['total_pages']==2
    assert len(first['items'])==100 and len(last['items'])==21
    assert len({r['id'] for r in first['items']+last['items']})==121


def test_failed_ai_attempts_respect_configured_daily_cap(db_session,context,monkeypatch):
    from backend.services.gemini_service import get_daily_ai_usage
    p,_,j=context;p.consent_given_for_ai=True;db_session.commit()
    monkeypatch.setenv('GEMINI_API_KEY','synthetic-key')
    monkeypatch.setenv('AI_DAILY_LIMIT','1')
    with patch('google.genai.Client',side_effect=RuntimeError('Synthetic offline failure')) as external:
        asyncio.run(analyze_job_with_ai(db_session,j,p))
        result=asyncio.run(analyze_job_with_ai(db_session,j,p))
        assert external.call_count==1
    assert result.engine_used=='rules_fallback'
    assert get_daily_ai_usage(db_session)['daily_used']==1
    assert get_daily_ai_usage(db_session)['daily_limit']==1


def test_changed_matching_preferences_expire_application_approval(db_session):
    from backend.tests.test_phase4 import phase4_job, documents, start_ready
    # Build real fixtures through their underlying functions with this isolated DB.
    job=phase4_job.__wrapped__(db_session)
    package_docs=documents.__wrapped__(db_session,job)
    application=start_ready(job,package_docs)
    pref=db_session.query(SearchPreference).first()
    pref.target_countries='["India"]';db_session.commit()
    assert client.get(f'/api/phase4/applications/{application}/browser-plan').status_code==409


def test_industry_credit_requires_candidate_industry_evidence():
    unrelated={'current_role':'EHS Manager','summary':'Office ergonomics','employment_history':[],'skills':[],'achievements':[],'qualifications':[],'certifications':[]}
    related={**unrelated,'summary':'Chemical manufacturing plant safety'}
    low=evaluate(unrelated,description='Lead EHS in chemical manufacturing plants.')
    high=evaluate(related,description='Lead EHS in chemical manufacturing plants.')
    assert low.score_breakdown['industry']==0
    assert high.score_breakdown['industry']>0


def test_partial_discovery_reports_feed_failures_and_filtered_counts(db_session, context):
    _, board, job = context
    other = EmployerBoard(company_name='Unavailable Employer', platform='lever', board_token='unavailable', is_enabled=True)
    db_session.add(other)
    db_session.commit()

    async def valid(_):
        return [raw(job), raw(job, source_job_id='software-1', url='https://boards.greenhouse.io/synthetic/jobs/software-1', title='Software Engineer', description='Build software')]

    async def missing(_):
        raise ValueError('404 Not Found')

    with patch('backend.services.discovery.GreenhouseConnector.fetch_jobs', valid), patch('backend.services.discovery.LeverConnector.fetch_jobs', missing):
        response = client.post('/api/search/run')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'partial'
    assert data['boards_succeeded'] == 1 and data['boards_failed'] == 1
    assert data['postings_fetched'] == 2 and data['jobs_found'] == 1
    assert '404 Not Found' in data['errors'][0]
    assert '1 failed' in data['message']
    history = client.get('/api/search/history').json()[0]
    assert history['status'] == 'partial'
    assert '2 postings fetched; 1 HSE vacancies accepted' in history['error_message']
    db_session.refresh(job)
    assert job.is_active and job.is_saved
