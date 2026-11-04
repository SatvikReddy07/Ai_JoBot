"""Run via Windows Task Scheduler; no email or external network activity."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.main import app  # initialize additive schema
from backend.app.database import SessionLocal
from backend.services.reminder_service import dispatch_due_reminders
if __name__ == "__main__":
    with SessionLocal() as db:
        print(f"Delivered {dispatch_due_reminders(db)} local reminders.")
