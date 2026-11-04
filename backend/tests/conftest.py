import sys
sys.modules["backend.tests.conftest"] = sys.modules[__name__]
import os
import tempfile
_test_data = tempfile.TemporaryDirectory(prefix="hse_tests_")
os.environ["HSE_DATA_DIR"] = _test_data.name
os.environ.pop("GEMINI_API_KEY", None)
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.models  # Ensure all models are registered in Base.metadata
from backend.app.main import app, get_or_create_user_profile
from backend.app.database import Base, get_db

from backend.services.discovery import init_default_boards, init_search_preferences

TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create all tables once for the test session
Base.metadata.create_all(bind=engine)

@pytest.fixture(autouse=True)
def setup_db():
    db = TestingSessionLocal()
    init_default_boards(db)
    init_search_preferences(db)
    get_or_create_user_profile(db)
    db.close()

    yield
    # Clean all rows between tests without dropping schema
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

client = TestClient(app)
