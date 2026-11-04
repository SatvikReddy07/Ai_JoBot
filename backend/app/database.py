import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Database path in data/hse_career.db
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(os.environ.get("HSE_DATA_DIR", str(BASE_DIR / "data"))).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "hse_career.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def initialize_schema():
    """Add missing tables only; take a consistent SQLite backup before migration."""
    import sqlite3
    from sqlalchemy import inspect
    if DB_PATH.exists():
        current = set(inspect(engine).get_table_names())
        missing = set(Base.metadata.tables) - current
        if missing:
            backup = DATA_DIR / "hse_career_phase4_auto_backup.db"
            if not backup.exists():
                with sqlite3.connect(str(DB_PATH)) as source, sqlite3.connect(str(backup)) as dest:
                    source.backup(dest)
    Base.metadata.create_all(bind=engine)
