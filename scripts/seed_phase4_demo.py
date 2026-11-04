import os,sys,json
from pathlib import Path
if not os.environ.get('HSE_DATA_DIR'):
    raise SystemExit('Set HSE_DATA_DIR to a disposable synthetic demo directory. Production data must not be seeded.')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.main import get_or_create_user_profile
from backend.app.database import SessionLocal
from backend.app.models import Job
from backend.services.package_service import create_application_package, approve_package
with SessionLocal() as db:
 p=get_or_create_user_profile(db)
 p.name='Synthetic Candidate';p.current_role='Regional EHS Manager';p.current_company='Synthetic Manufacturing';p.location='Hyderabad, India';p.summary='Environmental compliance, manufacturing safety and incident investigation experience.'
 p.qualifications='["M.Tech Environmental Engineering"]';p.skills='["Environmental Compliance", "Incident Investigation", "Process Safety"]';p.certifications='[]';p.employment_history='[]';p.achievements='[]';p.target_countries='["India", "Germany"]';db.commit()
 for n,country in enumerate(['India','Germany']):
  j=Job(source='lever',source_job_id=f'demo-{n}',company='Synthetic Employer '+str(n+1),title='Regional EHS Manager',description='Lead EHS governance and environmental compliance across manufacturing plants. ISO 14001 and ISO 45001. Visa sponsorship information not supplied.',location='Hyderabad, India' if country=='India' else 'Berlin, Germany',country=country,url=f'https://synthetic-employer.example.invalid/job/{n}',employment_type='Full-time',is_permanent_fulltime=True,is_active=True,match_score=85,match_level='Strong Match')
  db.add(j);db.commit()
  from backend.app.main import format_user_profile_response
  pkg=create_application_package(db,j,format_user_profile_response(p))
  approve_package(db,pkg,approved_by='Synthetic Candidate',notes='Synthetic test package approved for local demo.')
 j=Job(source='lever',source_job_id='unrelated-demo',company='Synthetic Software',title='Senior Software Engineering Manager',description='Build software APIs',location='India',country='India',url='https://synthetic-employer.example.invalid/software',employment_type='Full-time',is_permanent_fulltime=True,match_score=99,is_active=True)
 db.add(j);db.commit()
 print('Seeded synthetic-only demo data')
