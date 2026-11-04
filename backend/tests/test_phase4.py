import io
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
import pytest
from backend.tests.conftest import client
from backend.app.models import Job, UserProfile, ApplicationPackage, GeneratedDocument, JobApplication, FollowUpReminder, ApplicationEvent
from backend.services.package_service import PACKAGES_DIR
from backend.services.cv_parser import parse_cv_content
from backend.services.tailoring_service import generate_tailored_cv_rules, generate_tailored_cover_letter_rules
from backend.services.eligibility_service import assess_eligibility
from backend.services.portal_service import portal_info, validate_portal_url

P = "/api/phase4"

@pytest.fixture
def phase4_job(db_session):
    p = db_session.query(UserProfile).first()
    p.name = "Synthetic Candidate"; p.current_role = "EHS Manager"; p.current_company = "Synthetic Prior Employer"
    p.summary = "Environmental compliance and manufacturing safety experience."
    p.qualifications = json.dumps(["M.Tech Environmental Engineering"])
    p.skills = json.dumps(["Environmental Compliance", "Process Safety"])
    p.certifications = "[]"; p.achievements = "[]"; p.employment_history = "[]"
    p.target_countries = '["India", "Germany"]'
    job = Job(source="lever", source_job_id="synthetic-p4", company="Synthetic Employer", title="Regional EHS Manager",
        description="Lead manufacturing environmental compliance and process safety. NEBOSH certification required.",
        location="Berlin, Germany", country="Germany", employment_type="Full-time", is_permanent_fulltime=True,
        is_active=True, url="https://jobs.lever.co/synthetic/vacancy-001", match_score=85)
    db_session.add(job); db_session.commit(); db_session.refresh(job)
    return job

@pytest.fixture
def documents(db_session, phase4_job):
    directory = PACKAGES_DIR / "phase4_synthetic"; directory.mkdir(exist_ok=True)
    pkg = ApplicationPackage(job_id=phase4_job.id, template_name="global_regional_hse", status="approved", package_dir=str(directory))
    db_session.add(pkg); db_session.flush()
    docs=[]
    for kind in ["cv_docx", "cover_letter_docx"]:
        path=directory/(kind+".docx");path.write_bytes(b"Synthetic file bytes for approval digest")
        d=GeneratedDocument(package_id=pkg.id,doc_type=kind,filename=path.name,file_path=str(path),version_number=1,is_approved=True)
        db_session.add(d);docs.append(d)
    db_session.commit()
    return pkg,docs

def create(job):
    r=client.post(P+"/applications",json={"job_id":job.id});assert r.status_code==201,r.text
    return r.json()["id"]

def prepare(a, job, documents, **extra):
    pkg,docs=documents
    payload=dict(package_id=pkg.id,cv_document_id=docs[0].id,cover_letter_document_id=docs[1].id,
        application_url=job.url,questions=[],verified_fields={"name":"Synthetic Candidate","email":"synthetic@example.invalid"},
        profile_reviewed=True,official_url_verified=True)
    payload.update(extra)
    return client.put(f"{P}/applications/{a}/prepare",json=payload)

def approve(a):
    return client.post(f"{P}/applications/{a}/approve",json={"acknowledge_unknowns":True,"notes":"Reviewed synthetic facts and all eligibility unknowns."})

def start_ready(job,documents):
    a=create(job)
    assert prepare(a,job,documents).status_code==200
    assert approve(a).status_code==200
    assert client.post(f"{P}/applications/{a}/start").status_code==200
    return a

def test_upload_parser_preserves_confirmed_profile():
    existing=dict(name="Synthetic Candidate",employment_history=[{"role":"Maintenance Manager"}],certifications=[])
    assert parse_cv_content("Different text",existing)==existing
    result=parse_cv_content("Synthetic Candidate\nMaintenance Engineer\nSynthetic Employer")
    assert result['certifications']==[] and result['employment_history']==[] and result['achievements']==[]

def test_generation_uses_only_supplied_facts():
    p=dict(name="Synthetic Candidate",current_role="EHS Manager",current_company="Synthetic Employer",summary="Confirmed synthetic summary.",skills=[],qualifications=[],employment_history=[],certifications=[],achievements=[])
    cv=generate_tailored_cv_rules(p,"Target Employer","EHS Manager","")
    letter=generate_tailored_cover_letter_rules(p,"Target Employer","EHS Manager","Germany")
    assert cv.contact_email==cv.contact_phone==""
    assert "19" not in cv.summary and "dsm" not in cv.summary.lower()
    assert "dsm" not in " ".join(letter.body_paragraphs).lower()

def test_eligibility_unknowns_and_mandatory_gap(db_session,phase4_job):
    res=assess_eligibility(phase4_job,db_session.query(UserProfile).first())
    assert res['overall_status']=='requires_review'
    assert next(c for c in res['checks'] if c['category']=='work_authorization')['status']=='unknown'
    assert res['sponsorship_status']=='Unknown'
    assert any(c['category']=='certifications' and c['status']!='met' for c in res['checks'])

def test_unrelated_roles_excluded_from_queue(db_session,phase4_job):
    phase4_job.title="Senior Software Engineering Manager";phase4_job.description="Build software APIs";db_session.commit()
    assert client.get(P+'/queue').json()==[]
    assert client.post(P+'/applications',json={'job_id':phase4_job.id}).status_code==409

def test_duplicate_prevention(phase4_job):
    create(phase4_job)
    assert client.post(P+'/applications',json={'job_id':phase4_job.id}).status_code==409

def test_legacy_duplicate_prevention(db_session,phase4_job):
    phase4_job.application_status='Applied';db_session.commit()
    assert client.post(P+'/applications',json={'job_id':phase4_job.id}).status_code==409

def test_approval_requires_preparation(phase4_job):
    a=create(phase4_job)
    assert approve(a).status_code==409
    assert client.post(f'{P}/applications/{a}/start').status_code==409

def test_unapproved_package_rejected(db_session,phase4_job,documents):
    a=create(phase4_job);pkg,_=documents;pkg.status='draft';db_session.commit()
    assert prepare(a,phase4_job,documents).status_code==409

def test_wrong_document_kind_and_package(db_session,phase4_job,documents):
    a=create(phase4_job)
    assert prepare(a,phase4_job,documents,cv_document_id=documents[1][1].id).status_code==409
    documents[0].job_id=999;db_session.commit()
    assert prepare(a,phase4_job,documents).status_code==409

def test_questions_and_unknown_acknowledgment(phase4_job,documents):
    a=create(phase4_job)
    questions=[dict(question='Work authorization?',answer='',verified=False,mandatory=True)]
    assert prepare(a,phase4_job,documents,questions=questions).status_code==200
    assert approve(a).status_code==409
    assert prepare(a,phase4_job,documents).status_code==200
    assert client.post(f'{P}/applications/{a}/approve',json={'notes':'Reviewed facts'}).status_code==409
    assert approve(a).status_code==200

def test_manual_submission_and_followup(db_session,phase4_job,documents):
    a=start_ready(phase4_job,documents)
    assert client.post(f'{P}/applications/{a}/record-submission',json={'confirmation_reference':'','manually_submitted':True}).status_code==422
    assert client.post(f'{P}/applications/{a}/record-submission',json={'confirmation_reference':'MOCK-001','manually_submitted':False}).status_code==409
    r=client.post(f'{P}/applications/{a}/record-submission',json={'confirmation_reference':'MOCK-001','manually_submitted':True})
    assert r.status_code==200,r.text
    assert r.json()['status']=='submitted'
    reminder=db_session.query(FollowUpReminder).one()
    assert 6.9 < (reminder.due_date-datetime.utcnow()).total_seconds()/86400 < 7.1
    assert db_session.query(ApplicationEvent).count()>=5
    assert client.post(f'{P}/applications/{a}/record-submission',json={'confirmation_reference':'MOCK-001','manually_submitted':True}).status_code==409

def test_submission_without_reminder(db_session,phase4_job,documents):
    a=start_ready(phase4_job,documents)
    assert client.post(f'{P}/applications/{a}/record-submission',json={'confirmation_reference':'MOCK-001','manually_submitted':True,'follow_up_enabled':False}).status_code==200
    assert db_session.query(FollowUpReminder).count()==0

def test_document_change_invalidates_application(db_session,phase4_job,documents):
    a=start_ready(phase4_job,documents)
    documents[1][0].version_number=2;db_session.commit()
    assert client.get(f'{P}/applications/{a}/browser-plan').status_code==409
    assert client.post(f'{P}/applications/{a}/record-submission',json={'confirmation_reference':'MOCK-001','manually_submitted':True}).status_code==409

def test_file_tamper_invalidates_approval(phase4_job,documents):
    a=start_ready(phase4_job,documents)
    Path(documents[1][0].file_path).write_bytes(b'Tampered bytes')
    assert client.get(f'{P}/applications/{a}/browser-plan').status_code==409

def test_profile_change_invalidates_approval(db_session,phase4_job,documents):
    a=start_ready(phase4_job,documents)
    p=db_session.query(UserProfile).first();p.name='Changed Candidate';db_session.commit()
    assert client.get(f'{P}/applications/{a}/browser-plan').status_code==409

def test_confirmed_mandatory_gap_blocks_preparation(phase4_job,documents):
    a=create(phase4_job)
    r=client.post(f'{P}/applications/{a}/eligibility-review',json={'checks':[{'category':'certifications','status':'not_met','evidence':'User confirms required NEBOSH is not held.'}]})
    assert r.json()['overall_status']=='not_eligible'
    assert prepare(a,phase4_job,documents).status_code==409

def test_state_transitions_and_legacy_bypass(phase4_job):
    a=create(phase4_job)
    assert client.put(f'{P}/applications/{a}/status',json={'status':'submitted'}).status_code==409
    assert client.put(f'/api/jobs/{phase4_job.id}/status',json={'status':'Applied'}).status_code==409
    assert client.put(f'{P}/applications/{a}/status',json={'status':'withdrawn'}).status_code==200
    assert client.post(f'{P}/applications/{a}/start').status_code==409

def test_portal_adapter_hosts_and_unsafe_urls():
    for host,name in [('boards.greenhouse.io','greenhouse'),('jobs.lever.co','lever'),('x.myworkdayjobs.com','workday'),('www.linkedin.com','linkedin'),('www.naukri.com','naukri')]:
        assert portal_info(f'https://{host}/job')['name']==name
    for url in ['javascript:alert(1)','http://employer.example/job','https://127.0.0.1/job','https://user:password@example.com','https://localhost/job']:
        with pytest.raises(ValueError):validate_portal_url(url)
    assert portal_info('https://greenhouse.io.evil.example/job')['name']=='employer_portal'

def test_origin_and_host_controls():
    assert client.get('/health',headers={'host':'evil.example'}).status_code==400
    assert client.post(P+'/applications',headers={'origin':'https://evil.example'},json={'job_id':1}).status_code==403

def test_unknown_fields_rejected(phase4_job):
    assert client.post(P+'/applications',json={'job_id':phase4_job.id,'password':'do-not-store'}).status_code==422

def test_editable_outreach_no_sending(phase4_job):
    a=create(phase4_job)
    r=client.post(f'{P}/applications/{a}/outreach',json={'kind':'referral','channel':'linkedin'})
    assert r.status_code==200 and not r.json()['is_sent']
    assert 'Synthetic Prior Employer' in r.json()['message_body']
    d=r.json();body=dict(message_body=d['message_body'],subject=d['subject'])
    assert client.put(f"{P}/outreach/{d['id']}",json={**body,'manually_sent':True}).status_code==409
    assert client.put(f"{P}/outreach/{d['id']}",json={**body,'approved':True}).status_code==200
    assert client.put(f"{P}/outreach/{d['id']}",json={**body,'approved':True,'manually_sent':True}).json()['is_sent']
    assert client.post(f'{P}/applications/{a}/outreach',json={'kind':'follow_up'}).status_code==409

def test_reminder_update_and_dispatch_dedup(db_session,phase4_job):
    from backend.services.reminder_service import dispatch_due_reminders
    a=create(phase4_job)
    r=client.post(f'{P}/applications/{a}/reminders',json={'title':'Synthetic followup','due_date':(datetime.utcnow()-timedelta(minutes=1)).isoformat()})
    assert r.status_code==201
    with patch('backend.services.reminder_service.is_quiet_hours',return_value=False):
        assert dispatch_due_reminders(db_session,notify=lambda *_:True)==1
        assert dispatch_due_reminders(db_session,notify=lambda *_:True)==0
    assert client.put(f"{P}/reminders/{r.json()['id']}",json={'is_dismissed':True}).status_code==200

def test_failed_notification_is_retryable(db_session,phase4_job):
    from backend.services.reminder_service import dispatch_due_reminders
    a=create(phase4_job)
    client.post(f'{P}/applications/{a}/reminders',json={'title':'Retry','due_date':(datetime.utcnow()-timedelta(minutes=1)).isoformat()})
    with patch('backend.services.reminder_service.is_quiet_hours',return_value=False):
        assert dispatch_due_reminders(db_session,notify=lambda *_:False)==0
        assert dispatch_due_reminders(db_session,notify=lambda *_:True)==1

def test_upload_preserves_profile_and_limits(db_session):
    import docx
    p=db_session.query(UserProfile).first();p.name='Confirmed Candidate';p.certifications='[]';db_session.commit()
    d=docx.Document();d.add_paragraph('Unverified Different Candidate');buf=io.BytesIO();d.save(buf)
    r=client.post('/api/profile/upload-cv',files={'file':('../untrusted.docx',buf.getvalue(),'application/vnd.openxmlformats-officedocument.wordprocessingml.document')})
    assert r.status_code==200,r.text
    assert r.json()['profile']['name']=='Confirmed Candidate'
    assert r.json()['profile']['certifications']==[]
    assert r.json()['filename']=='untrusted.docx'
    assert client.post('/api/profile/upload-cv',files={'file':('bad.doc',b'test')}).status_code==400
    assert client.post('/api/profile/upload-cv',files={'file':('large.pdf',b'x'*(10*1024*1024+1))}).status_code==413

def test_browser_plan_does_not_submit(phase4_job,documents):
    a=start_ready(phase4_job,documents)
    plan=client.get(f'{P}/applications/{a}/browser-plan').json()
    assert plan['final_submission']=='manual_only'
    assert len(plan['documents'])==2
    assert client.get(P+'/applications').json()[0]['date_submitted'] is None

def test_cross_source_duplicate_url(db_session,phase4_job):
    create(phase4_job)
    other=Job(source='greenhouse',source_job_id='different-source',company=phase4_job.company,title=phase4_job.title,
        description=phase4_job.description,location=phase4_job.location,country=phase4_job.country,
        url=phase4_job.url+'?utm_source=other',employment_type='Full-time',is_permanent_fulltime=True)
    db_session.add(other);db_session.commit()
    assert client.post(P+'/applications',json={'job_id':other.id}).status_code==409

def test_additive_migration_preserves_data(tmp_path,monkeypatch):
    import sqlite3
    from sqlalchemy import create_engine
    from backend.app import database
    path=tmp_path/'legacy.db'
    with sqlite3.connect(path) as c:
        c.execute('CREATE TABLE preserved (value TEXT)');c.execute("INSERT INTO preserved VALUES ('synthetic-marker')")
    engine=create_engine('sqlite:///'+str(path))
    monkeypatch.setattr(database,'DB_PATH',path);monkeypatch.setattr(database,'DATA_DIR',tmp_path);monkeypatch.setattr(database,'engine',engine)
    database.initialize_schema()
    with sqlite3.connect(path) as c:
        assert c.execute('SELECT value FROM preserved').fetchone()[0]=='synthetic-marker'
        assert c.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        assert c.execute("SELECT name FROM sqlite_master WHERE name='job_applications'").fetchone()
    assert (tmp_path/'hse_career_phase4_auto_backup.db').exists()
    engine.dispose()

def test_eligibility_reviews_preserve_previous_evidence(phase4_job):
    a=create(phase4_job)
    for category in ['work_authorization','seniority']:
        r=client.post(f'{P}/applications/{a}/eligibility-review',json={'checks':[{'category':category,'status':'met','evidence':'Synthetic user-confirmed evidence for testing.'}]})
        assert r.status_code==200
    checks=r.json()['checks']
    assert next(c for c in checks if c['category']=='work_authorization')['status']=='met'

@pytest.mark.browser
def test_mock_portal_browser_workflow(phase4_job,documents):
    import os
    if os.getenv('HSE_RUN_BROWSER_TESTS') != '1': pytest.skip('Set HSE_RUN_BROWSER_TESTS=1 after installing Chromium.')
    from http.server import HTTPServer
    from threading import Thread
    from playwright.sync_api import sync_playwright
    from scripts.mock_employer_portal import Handler
    from scripts.assist_application import fill_supported_fields
    a=start_ready(phase4_job,documents)
    server=HTTPServer(('127.0.0.1',0),Handler)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            page=browser.new_page()
            page.goto(f'http://127.0.0.1:{server.server_port}')
            result=fill_supported_fields(page,{'name':'Synthetic Candidate','email':'synthetic@example.invalid'},
                {'cv':documents[1][0].file_path,'cover_letter':documents[1][1].file_path})
            assert result['submitted'] is False
            assert page.locator('input[name="name"]').input_value()=='Synthetic Candidate'
            assert page.locator('input[name="cv"]').evaluate('(e) => e.files.length')==1
            assert page.locator('#confirmation').text_content()==''
            assert client.get(P+'/applications').json()[0]['date_submitted'] is None
            # Test actor stands in for the user's final click; helper never clicks.
            page.get_by_role('button',name='Submit manually (mock)').click()
            confirmation=page.locator('#confirmation').text_content()
            assert confirmation=='MOCK-LOCAL-001'
            response=client.post(f'{P}/applications/{a}/record-submission',json={'confirmation_reference':confirmation,'manually_submitted':True})
            assert response.status_code==200 and response.json()['status']=='submitted'
            browser.close()
    finally:
        server.shutdown();server.server_close();thread.join(timeout=3)


def test_browser_failure_never_records_submission(phase4_job,documents):
    from scripts.assist_application import fill_supported_fields
    from unittest.mock import Mock
    a=start_ready(phase4_job,documents)
    page=Mock();page.locator.side_effect=TimeoutError('Synthetic unsupported form')
    with pytest.raises(TimeoutError):fill_supported_fields(page,{'name':'Synthetic Candidate'}, {})
    assert client.get(P+'/applications').json()[0]['date_submitted'] is None

def test_master_cv_download_containment(db_session,tmp_path):
    from backend.app.models import MasterCV
    outside=tmp_path/'private.txt';outside.write_text('Not a CV')
    row=MasterCV(filename='private.txt',file_type='pdf',stored_path=str(outside),raw_text='',file_size=8,is_active=True)
    db_session.add(row);db_session.commit()
    assert client.get('/api/profile/cv/download').status_code==403

@pytest.mark.parametrize('clause', [
    'A degree in law is required.',
    'A master degree in computer science is required.',
    'NEBOSH Diploma required.',
    'Ten years pharmaceutical manufacturing experience required.'
])
def test_keyword_overlap_does_not_verify_specific_requirement(db_session,phase4_job,clause):
    p=db_session.query(UserProfile).first()
    p.qualifications='["Master degree in Environmental Engineering"]'
    p.certifications='["NEBOSH IGC"]'
    p.employment_history='[{"highlights":["Manufacturing safety"]}]'
    phase4_job.description += '\n'+clause
    res=assess_eligibility(phase4_job,p)
    checks=[c for c in res['checks'] if clause.rstrip('.') in c['detail']]
    assert checks
    assert all(c['status']=='requires_review' for c in checks)

@pytest.mark.parametrize('field,value', [
    ('location','Changed city, Germany'),
    ('company','Different Employer'),
    ('employment_type','Contract'),
    ('is_permanent_fulltime',False)
])
def test_vacancy_change_invalidates_preparation_approval(db_session,phase4_job,documents,field,value):
    a=start_ready(phase4_job,documents)
    setattr(phase4_job,field,value);db_session.commit()
    assert client.get(f'{P}/applications/{a}/browser-plan').status_code==409


def test_sent_outreach_is_immutable_history(db_session,phase4_job):
    from backend.app.models import RecruiterOutreach
    a=create(phase4_job)
    draft=client.post(f'{P}/applications/{a}/outreach',json={'kind':'recruiter'}).json()
    body=dict(message_body=draft['message_body'],subject=draft['subject'],approved=True)
    assert client.put(f"{P}/outreach/{draft['id']}",json=body).status_code==200
    assert client.put(f"{P}/outreach/{draft['id']}",json={**body,'manually_sent':True}).status_code==200
    assert client.put(f"{P}/outreach/{draft['id']}",json={**body,'message_body':'Overwritten draft'}).status_code==409
    row=db_session.get(RecruiterOutreach,draft['id'])
    assert row.is_sent and row.message_body==draft['message_body']
    history=client.get(f'{P}/applications/{a}/history').json()
    assert any(e['details'].get('manually_sent') and e['details'].get('message_body')==draft['message_body'] for e in history)


def test_document_defaults_do_not_invent_contact_details():
    from backend.app.schemas import TailoredCoverLetterContent, TailoredCVContent
    letter=TailoredCoverLetterContent(date_str='2026-11-04',company_name='Synthetic Employer',job_title='EHS Manager')
    cv=TailoredCVContent(summary='Reviewed facts',target_job_title='EHS Manager',target_company='Synthetic Employer')
    assert letter.candidate_contact==''
    assert cv.contact_email==cv.contact_phone==cv.contact_location==cv.contact_linkedin==''
