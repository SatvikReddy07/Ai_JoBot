import os
import subprocess
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from backend.app.models import Job, DesktopNotificationLog

logger = logging.getLogger(__name__)

def is_quiet_hours(start_hour: int = 22, end_hour: int = 7) -> bool:
    """Checks if current local time is within quiet hours."""
    current_hour = datetime.now().hour
    if start_hour > end_hour:
        # e.g., 22:00 to 07:00 next day
        return current_hour >= start_hour or current_hour < end_hour
    else:
        return start_hour <= current_hour < end_hour

def send_windows_notification(title: str, message: str) -> bool:
    """
    Sends native Windows desktop toast notification via PowerShell at ₹0 cost.
    Completely offline and secure.
    """
    import base64
    title64 = base64.b64encode(title.encode("utf-8")).decode("ascii")
    message64 = base64.b64encode(message.encode("utf-8")).decode("ascii")
    ps_script = f"""
$title = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{title64}'))
$message = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{message64}'))
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$textNodes = $template.GetElementsByTagName("text")
$textNodes.Item(0).AppendChild($template.CreateTextNode($title)) > $null
$textNodes.Item(1).AppendChild($template.CreateTextNode($message)) > $null
$toast = [Windows.UI.Notifications.ToastNotification]::new($template)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("HSE Career Agent").Show($toast)
"""
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=5
        )
        return res.returncode == 0
    except Exception as exc:
        logger.warning(f"Could not dispatch Windows toast notification: {exc}")
        return False

def check_and_notify_high_match_job(
    db: Session,
    job: Job,
    min_score: int = 85,
    respect_quiet: bool = True,
    quiet_start: int = 22,
    quiet_end: int = 7
) -> Optional[DesktopNotificationLog]:
    """
    Checks if job qualifies for desktop notification:
    - Score >= min_score (default 85)
    - Not previously notified
    - Not in quiet hours (if enabled)
    """
    if job.match_score < min_score:
        return None

    # Check for duplicates
    existing = db.query(DesktopNotificationLog).filter(
        DesktopNotificationLog.job_id == job.id
    ).first()
    if existing:
        return None

    # Check quiet hours
    if respect_quiet and is_quiet_hours(quiet_start, quiet_end):
        logger.info(f"Skipping notification for job {job.id} during quiet hours.")
        return None

    score_type = "AI Match" if (job.ai_assessment and job.ai_assessment.engine_used == "ai") else "Rules Match"
    title = f"🎯 High Match HSE Opportunity ({job.match_score}/100)"
    message = f"{job.title} at {job.company} [{job.location}] - {score_type}. Click to open dashboard."

    sent = send_windows_notification(title, message)

    log_entry = DesktopNotificationLog(
        job_id=job.id,
        match_score=job.match_score,
        notification_type="high_match",
        status="sent" if sent else "logged",
        notified_at=datetime.utcnow()
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry
