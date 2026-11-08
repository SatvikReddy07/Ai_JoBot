"""Synthetic regressions for the live discovery coverage findings."""
import html
import pytest
from backend.app.models import EmployerBoard, Job
from backend.connectors.base import clean_html, parse_location
from backend.services.discovery import DEFAULT_BOARDS, LEGACY_BOARDS, CATALOG_MARKER, init_default_boards, is_hse_relevant
from backend.services.matcher import HSEJobMatcher


def test_encoded_greenhouse_html_leaves_readable_evidence():
    markup='<p>Lead environmental compliance.</p><p>ISO 14001 and pollution control.</p>'
    assert clean_html(html.escape(markup)) == 'Lead environmental compliance.\nISO 14001 and pollution control.'
    assert clean_html(html.escape(html.escape(markup))) == clean_html(markup)
    assert 'do_not_keep' not in clean_html('<script>do_not_keep</script><p>HSE</p>')


@pytest.mark.parametrize('title',[
    'Manager Health, Safety & Environment (w/m/d)',
    'Environmental Management Specialist', 'WHS Manager', 'OHS Lead',
    'Process Safety Engineers & Senior Process Safety Consultants', 'PSM Manager', 'HAZOP Consultant', 'Loss Prevention Manager',
    'HSSE Manager', 'Manager, Environmental Health and Safety (EH&S)',
])
def test_discovery_recognizes_hse_and_environment_titles(title):
    assert is_hse_relevant(title, '')
    assert HSEJobMatcher().classify_occupational_relevance(title, '')[1]


@pytest.mark.parametrize('title',[
    'Senior Product Manager, Trust & Safety, Integrity and Fraud',
    'Trust & Safety Specialist', 'Senior Backend Engineer, Development Health',
    'Manager of Health Insurance Renewals Team', 'Functional Safety Engineer', 'Functional Safety Manager', 'Trust & Safety Manager',
    'Manager, System Safety Engineering', '(Senior) Systems and Safety Engineer',
    'Environmental Test Engineer', 'Sales Manager', 'Automation Electrician',
    'Managing Director', 'Legal Counsel, Real Estate & Construction',
    'Associate Scientist, Analytics', 'Subject Matter Expert - Mechanical',
])
def test_other_domains_do_not_enter_hse_discovery(title):
    assert not is_hse_relevant(title, 'Follow company health and safety policies. ISO 45001 compliance. Report to the HSE Manager. Emergency response and incident investigation.')


@pytest.mark.parametrize('location,country',[
    ('Kiruna, Sweden','Sweden'), ('Andenes, Norway','Norway'),
    ('Copenhagen, Denmark','Denmark'), ('Boston, United States','United States'),
    ('Toronto, Canada','Canada'), ('Sydney, New South Wales, Australia','Australia'),
])
def test_added_source_locations_remain_explicit(location,country):
    assert parse_location(location)[1] == country


def test_catalog_upgrade_preserves_jobs_custom_boards_and_disabled_choices(db_session):
    db_session.query(EmployerBoard).delete()
    for company, platform, token in LEGACY_BOARDS:
        db_session.add(EmployerBoard(company_name=company, platform=platform, board_token=token, is_enabled=token!='stripe'))
    custom=EmployerBoard(company_name='Synthetic Custom',platform='lever',board_token='custom',is_enabled=False)
    # Existing user-disabled new board must not be re-enabled by catalog expansion.
    disabled=EmployerBoard(**{**DEFAULT_BOARDS[0],'is_enabled':False})
    job=Job(source='greenhouse',source_job_id='saved-old',company='Canva',title='HSE Manager',location='Synthetic Location',description='Synthetic safety duties',url='https://example.org/job',is_active=True,is_saved=True)
    db_session.add_all([custom,disabled,job]);db_session.commit()
    init_default_boards(db_session)
    for token in ['canva','atlassian','miro']:
        board=db_session.query(EmployerBoard).filter_by(board_token=token).one()
        assert not board.is_enabled and board.last_status == CATALOG_MARKER
    assert not db_session.query(EmployerBoard).filter_by(board_token='stripe').one().is_enabled
    assert not disabled.is_enabled and not custom.is_enabled
    assert job.is_active and job.is_saved
    count=db_session.query(EmployerBoard).count()
    init_default_boards(db_session)
    assert db_session.query(EmployerBoard).count() == count
    # Respect subsequent deliberate deletions and re-enabling.
    removed=db_session.query(EmployerBoard).filter_by(board_token=DEFAULT_BOARDS[-1]['board_token']).one()
    db_session.delete(removed)
    retired=db_session.query(EmployerBoard).filter_by(board_token='canva').one()
    retired.is_enabled=True;db_session.commit()
    init_default_boards(db_session)
    assert retired.is_enabled and db_session.query(EmployerBoard).count() == count-1


def test_custom_catalog_is_not_silently_replaced(db_session):
    db_session.query(EmployerBoard).delete()
    db_session.add(EmployerBoard(company_name='Synthetic',platform='lever',board_token='only-custom',is_enabled=False));db_session.commit()
    init_default_boards(db_session)
    assert db_session.query(EmployerBoard).count() == 1


def test_european_native_board_ownership_is_exact():
    from types import SimpleNamespace
    from backend.services.discovery import belongs_to_board
    board=SimpleNamespace(platform='greenhouse',company_name='Synthetic',board_token='synthetic')
    job=SimpleNamespace(source='greenhouse',company='Synthetic',url='https://job-boards.eu.greenhouse.io/synthetic/jobs/1')
    assert belongs_to_board(job,board)
    job.url='https://job-boards.eu.greenhouse.io/another/jobs/1'
    assert not belongs_to_board(job,board)


def test_fresh_catalog_contains_only_verified_defaults_and_is_idempotent(db_session):
    db_session.query(EmployerBoard).delete();db_session.commit()
    init_default_boards(db_session)
    assert {b.board_token for b in db_session.query(EmployerBoard)} == {b['board_token'] for b in DEFAULT_BOARDS}
    init_default_boards(db_session)
    assert db_session.query(EmployerBoard).count() == len(DEFAULT_BOARDS)
