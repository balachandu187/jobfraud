"""
Pytest fixtures.

Each test module gets an isolated SQLite database (via a temporary file) so tests never
touch the demo data in `database/jobshield_v3.db`. The FastAPI dependency override swaps
the session factory for the test one.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Make `backend` importable when pytest is run from the repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database.connection import get_db  # noqa: E402
from backend.database.models import Base  # noqa: E402


@pytest.fixture()
def db_session():
    """Yields a Session bound to a throwaway SQLite file."""
    with tempfile.TemporaryDirectory() as tmp:
        url = f"sqlite:///{os.path.join(tmp, 'test.db')}"
        engine = create_engine(url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()
            engine.dispose()


@pytest.fixture()
def client(db_session):
    """TestClient whose DB dependency points at the isolated test database."""
    from backend.main import app

    def _override() -> object:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
