"""Optional visible Playwright helper. Never clicks buttons or submits a form.

Run after approval and 'Open portal and begin' in the Control Center:
  python scripts/assist_application.py APPLICATION_ID --allow-host boards.greenhouse.io
Default mode prints a manual checklist. Add --fill to populate supported fields
in a fresh visible browser. Login and CAPTCHA remain manual. No passwords stored.
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

FIELDS = {"name": ["name", "full_name"], "email": ["email"], "phone": ["phone"],
          "location": ["location"], "current_company": ["company"], "current_role": ["current_role"]}

def fill_supported_fields(page, fields, documents):
    """Only exact input-name allowlist; no arbitrary selectors or button clicks."""
    filled, missing = [], []
    for key, value in fields.items():
        if not value or key not in FIELDS: continue
        selectors = ", ".join(f'input[name="{name}"]:not([type="hidden"]):not([type="password"]):not([type="submit"]):not([type="button"]):not([type="file"]):not([type="checkbox"]):not([type="radio"])' for name in FIELDS[key])
        loc = page.locator(selectors)
        if loc.count() == 1 and loc.is_visible() and loc.is_editable():
            loc.fill(value); filled.append(key)
        else: missing.append(key)
    for kind, filename in documents.items():
        loc = page.locator(f'input[type="file"][name="{kind}"]')
        if loc.count() == 1:
            loc.set_input_files(str(filename)); filled.append(kind)
        else: missing.append(kind)
    return dict(filled=filled, manual=missing, submitted=False)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("application_id", type=int)
    parser.add_argument("--allow-host", required=True, help="Exact host you verified for this employer")
    parser.add_argument("--fill", action="store_true")
    args = parser.parse_args()
    base = "http://127.0.0.1:8000"
    def get_plan():
        with urlopen(f"{base}/api/phase4/applications/{args.application_id}/browser-plan", timeout=10) as response:
            return json.load(response)
    try:
        plan = get_plan()
        if urlsplit(plan["url"]).hostname != args.allow_host: raise ValueError("Portal host differs from your allowlist.")
        if not args.fill:
            print("Manual workflow: open the verified portal, authenticate, copy reviewed fields, upload approved documents, review and submit yourself.")
            return
        from playwright.sync_api import sync_playwright
        with tempfile.TemporaryDirectory(prefix="hse_assist_") as temp, sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False)
            page = browser.new_page()
            page.goto(plan["url"], wait_until="domcontentloaded", timeout=30000)
            input("Authenticate and open the application form manually. Press Enter to fill supported fields (no submission): ")
            if urlsplit(page.url).hostname != args.allow_host: raise ValueError("Portal redirected to another host; use manual preparation.")
            plan = get_plan()  # recheck approval after login / user delay
            paths = {}
            for doc in plan["documents"]:
                path = Path(temp) / Path(doc["filename"]).name
                with urlopen(base + doc["download_path"], timeout=15) as response:
                    path.write_bytes(response.read())
                paths[doc["kind"]] = path
            print(json.dumps(fill_supported_fields(page, plan["fields"], paths)))
            input("Review all fields and documents. Final submission is manual. Press Enter when finished to close the session: ")
            browser.close()
    except Exception as exc:
        print(f"Assistance unavailable: {exc}. Continue with the Control Center manual checklist.", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
