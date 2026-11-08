from playwright.sync_api import sync_playwright, expect
from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True)
 context=browser.new_context(viewport={'width':1440,'height':1000})
 page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:3000',wait_until='networkidle')
 page.get_by_role('button',name='Application Control Center',exact=True).click()
 expect(page.get_by_role('heading',name='Application Control Center',exact=True).last).to_be_visible()
 expect(page.get_by_text('Synthetic Employer 1',exact=False).first).to_be_visible()
 assert page.get_by_text('Senior Software Engineering Manager',exact=False).count()==0
 page.get_by_role('button',name='Review',exact=True).first.click()
 page.get_by_role('button',name='Shortlist vacancy',exact=True).click()
 expect(page.get_by_role('button',name='Save preparation',exact=True)).to_be_visible()
 page.get_by_label('Package',exact=True).select_option(index=1)
 page.get_by_label('CV version',exact=True).select_option(index=1)
 page.get_by_label('Cover-letter version',exact=True).select_option(index=1)
 page.get_by_text('I reviewed the candidate facts and selected documents.',exact=False).click()
 page.get_by_text('I verified this application URL belongs',exact=False).click()
 page.get_by_label('name',exact=True).fill('Synthetic Candidate')
 page.get_by_label('email',exact=True).fill('synthetic@example.invalid')
 page.get_by_role('button',name='Save preparation',exact=True).click()
 expect(page.get_by_role('status')).to_contain_text('Preparation saved')
 page.get_by_text('I reviewed unresolved eligibility information',exact=False).click()
 page.get_by_label('Approval notes',exact=True).fill('Reviewed synthetic-only documents and all eligibility unknowns.')
 page.get_by_role('button',name='Approve preparation',exact=True).click()
 expect(page.get_by_role('status')).to_contain_text('Preparation approved')
 # The test browser supplies a local response for the fake HTTPS employer domain; no employer requests.
 import sys
 sys.path.insert(0,str(root))
 from scripts.mock_employer_portal import HTML
 context.route('https://synthetic-employer.example.invalid/**',lambda route:route.fulfill(status=200,content_type='text/html',body=HTML))
 with page.expect_popup() as popup:
  page.get_by_role('button',name='Open portal and begin',exact=True).click()
 portal=popup.value;portal.wait_for_load_state()
 expect(portal.get_by_role('heading',name='Synthetic employer portal')).to_be_visible()
 assert portal.locator('#confirmation').text_content()==''
 # Test actor manually confirms mock submission.
 portal.get_by_role('button',name='Submit manually (mock)').click()
 reference=portal.locator('#confirmation').text_content();portal.close()
 page.get_by_label('Employer confirmation number or confirmation-email reference',exact=True).fill(reference)
 page.get_by_text('I submitted this application manually and received confirmation.',exact=False).click()
 page.get_by_role('button',name='Record confirmed submission',exact=True).click()
 expect(page.get_by_role('status')).to_contain_text('Manual submission recorded')
 expect(page.get_by_text('Local reminders',exact=True)).to_be_visible()
 page.get_by_role('button',name='Draft message',exact=True).click()
 expect(page.get_by_label('Message body',exact=True)).to_contain_text('Synthetic Candidate')
 page.get_by_role('button',name='Close',exact=True).click()
 page.get_by_role('button',name='Application Tracker',exact=True).click()
 expect(page.get_by_text('Synthetic tracker role 120',exact=True)).to_be_visible()
 expect(page.get_by_text('Submitted',exact=True)).to_be_visible()
 assert not errors,errors
 print(json.dumps({'ui_workflow':'passed','unrelated_role_excluded':True,'approval_workflow':'passed','mock_portal':'passed','manual_submission_record':'passed','outreach_draft':'passed','tracker_pagination':'passed','phase4_tracker_stage':'passed','javascript_errors':errors}))
 browser.close()
