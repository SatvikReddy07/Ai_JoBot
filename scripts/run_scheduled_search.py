"""
HSE Career Agent - Automated Daily Scheduled Search Runner
Executes headless job discovery across all enabled employer career boards,
scores vacancies against Raghunath Reddy's profile, and records persistence in SQLite.
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# Set up project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database import SessionLocal
from backend.services.discovery import run_discovery_service

# Setup logging
LOG_DIR = PROJECT_ROOT / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "scheduled_search.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("scheduled_search")

LOCK_FILE = PROJECT_ROOT / "data" / "search.lock"

def acquire_lock() -> bool:
    if LOCK_FILE.exists():
        # Check lock file age (if older than 1 hour, consider stale)
        mtime = LOCK_FILE.stat().st_mtime
        age = datetime.now().timestamp() - mtime
        if age > 3600:
            logger.warning("Stale search lock detected (>1h). Overriding.")
            LOCK_FILE.unlink(missing_ok=True)
        else:
            logger.warning(f"Search already in progress. Lock file exists: {LOCK_FILE}")
            return False
    try:
        LOCK_FILE.write_text(f"pid={os.getpid()}\nstarted={datetime.utcnow().isoformat()}", encoding="utf-8")
        return True
    except Exception as e:
        logger.error(f"Failed to acquire lock: {e}")
        return False

def release_lock():
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except Exception as e:
        logger.error(f"Failed to release lock: {e}")

async def main():
    logger.info("=== Starting HSE Career Agent Automated Search ===")
    if not acquire_lock():
        logger.warning("Skipping execution: Another search process is active.")
        sys.exit(0)

    db = SessionLocal()
    try:
        summary = await run_discovery_service(db)
        logger.info(
            f"Search Completed Successfully. Status: {summary['status']} | "
            f"Boards Searched: {summary['boards_searched']} | "
            f"New Jobs Discovered: {summary['jobs_new']} | "
            f"Jobs Verified/Updated: {summary['jobs_updated']}"
        )
        if summary.get("errors"):
            logger.warning(f"Board Warnings/Errors: {summary['errors']}")
    except Exception as exc:
        logger.error(f"Critical error during scheduled search execution: {exc}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()
        release_lock()
        logger.info("=== Finished Scheduled Search Run ===\n")

if __name__ == "__main__":
    asyncio.run(main())
