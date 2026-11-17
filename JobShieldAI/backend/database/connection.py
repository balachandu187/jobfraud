"""
Database engine, session management and startup initialisation.

Responsibilities
----------------
* Create the engine and session factory (SQLite, WAL mode, foreign keys on).
* Provide `get_db()` as a FastAPI dependency with proper commit/rollback/close.
* Create tables automatically on startup (`init_db`).
* Import rows from the pre-SQLAlchemy `jobshield.db` exactly once, so the audit history
  shown in the UI survives the migration instead of appearing to have been wiped.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from sqlalchemy import create_engine, event, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings
from backend.database.models import Base, JobScan

logger = logging.getLogger(__name__)

engine: Engine = create_engine(
    settings.database_url,
    echo=settings.sql_echo,
    future=True,
    # SQLite blocks the writer while a reader holds the file; a longer timeout avoids
    # spurious "database is locked" errors during the scan-history dashboard reads.
    connect_args={"timeout": 15, "check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_connection: Any, _record: Any) -> None:
    """Enables WAL (concurrent readers) and foreign keys on every new connection."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
    except sqlite3.DatabaseError:  # pragma: no cover - read-only or damaged file
        logger.warning("Could not apply SQLite pragmas", exc_info=True)
    finally:
        cursor.close()


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------
def get_db() -> Iterator[Session]:
    """FastAPI dependency: yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope for scripts and background work."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------
def init_db() -> None:
    """Creates tables if missing, then imports any legacy audit rows once."""
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    logger.info("Database ready at %s", settings.database_path)
    _import_legacy_scans()


def _import_legacy_scans() -> None:
    """
    Copies rows from the previous SQLite schema into `job_scans` exactly once.

    The legacy file is only read — never modified — so an interrupted import is safe to
    retry. A marker file records that the migration ran.
    """
    legacy: Path = settings.legacy_database_path
    marker = legacy.with_suffix(".migrated")
    if not legacy.exists() or marker.exists():
        return

    try:
        source = sqlite3.connect(f"file:{legacy}?mode=ro", uri=True)
        source.row_factory = sqlite3.Row
        rows: List[sqlite3.Row] = source.execute(
            "SELECT id, timestamp, job_title, company_name, job_text, prediction,"
            " risk_score, risk_level, warnings_json, source_url, source_type FROM scans"
        ).fetchall()
        source.close()
    except sqlite3.DatabaseError as exc:
        logger.warning("Skipping legacy import (%s)", exc)
        return

    if not rows:
        marker.touch()
        return

    imported = 0
    with session_scope() as db:
        existing = db.execute(select(JobScan.id)).scalars().first()
        if existing is not None:
            # A v3 database already has data; do not duplicate history.
            marker.touch()
            return

        for row in rows:
            try:
                flags = json.loads(row["warnings_json"] or "[]")
            except (TypeError, ValueError):
                flags = []
            risk_level = row["risk_level"] or "Low Risk"
            db.add(JobScan(
                job_title=row["job_title"] or "",
                company_name=row["company_name"] or "",
                job_description=row["job_text"] or "",
                salary="",
                contact_email="",
                prediction=row["prediction"] or "Unknown",
                ml_prediction="Unknown",
                ml_probability=0.0,
                risk_score=int(row["risk_score"] or 0),
                risk_level=risk_level,
                rule_score=int(row["risk_score"] or 0),
                detected_flags=flags,
                recommendations=[],
                score_breakdown={"migrated_from": "jobshield.db"},
                source_type=row["source_type"] or "text",
                source_url=row["source_url"] or "",
            ))
            imported += 1

    marker.touch()
    logger.info("Imported %d legacy scan record(s) into job_scans", imported)


def health() -> Dict[str, Any]:
    """Database readiness probe used by /api/health."""
    try:
        with engine.connect() as conn:
            total = conn.execute(text("SELECT COUNT(*) FROM job_scans")).scalar_one()
            integrity = conn.execute(text("PRAGMA integrity_check")).scalar_one()
        return {"ok": integrity == "ok", "integrity": integrity, "rows": int(total),
                "path": str(settings.database_path)}
    except Exception as exc:  # pragma: no cover - damaged/locked file
        return {"ok": False, "error": str(exc), "path": str(settings.database_path)}
