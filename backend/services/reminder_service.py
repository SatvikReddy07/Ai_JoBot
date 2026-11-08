"""Local reminders with cross-process duplicate prevention via a SQLite write lock."""
from datetime import datetime
from sqlalchemy import text
from backend.app.models import FollowUpReminder, ReminderDelivery
from backend.services.notification_service import send_desktop_notification, is_quiet_hours


def dispatch_due_reminders(db, notify=send_desktop_notification, now=None):
    now = now or datetime.utcnow()
    if is_quiet_hours(): return 0
    count = 0
    # A reserved write lock prevents overlapping scheduled runs from dispatching twice.
    db.execute(text("BEGIN IMMEDIATE"))
    try:
        due = db.query(FollowUpReminder).filter(FollowUpReminder.due_date <= now,
            FollowUpReminder.is_completed.is_(False), FollowUpReminder.is_dismissed.is_(False)).all()
        for reminder in due:
            if reminder.snooze_until and reminder.snooze_until > now: continue
            if db.query(ReminderDelivery).filter_by(reminder_id=reminder.id).first(): continue
            if notify("HSE Career Agent reminder", reminder.title):
                db.add(ReminderDelivery(reminder_id=reminder.id, delivered_at=now))
                app = reminder.application
                if app and app.status == "submitted" and reminder.reminder_type == "follow_up":
                    from backend.app.phase4 import set_stage
                    set_stage(db, app, "follow_up_due", "Local follow-up reminder delivered.")
                count += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    return count
