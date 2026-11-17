"""
Database access layer (CRUD).

Routers and services never build queries themselves — they call these functions. That
keeps SQL in one place and makes the query behaviour easy to test.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.database.models import JobScan

LOW = "Low Risk"
MEDIUM = "Medium Risk"
HIGH = "High Risk"
RISK_LEVELS = (LOW, MEDIUM, HIGH)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
def create_scan(db: Session, **fields: Any) -> JobScan:
    """Persists one scan. Keyword arguments map onto JobScan columns."""
    scan = JobScan(**fields)
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------
def get_scan(db: Session, scan_id: int) -> Optional[JobScan]:
    return db.get(JobScan, scan_id)


def list_scans(
    db: Session,
    *,
    limit: int = 100,
    offset: int = 0,
    risk_level: Optional[str] = None,
    search: Optional[str] = None,
) -> List[JobScan]:
    """Newest-first scan list with optional tier filter and free-text search."""
    stmt = select(JobScan)
    if risk_level:
        stmt = stmt.where(JobScan.risk_level == risk_level)
    if search:
        needle = f"%{search.strip()}%"
        stmt = stmt.where(or_(
            JobScan.job_title.ilike(needle),
            JobScan.company_name.ilike(needle),
            JobScan.job_description.ilike(needle),
        ))
    stmt = stmt.order_by(JobScan.created_at.desc(), JobScan.id.desc()).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all())


def count_scans(db: Session, risk_level: Optional[str] = None) -> int:
    stmt = select(func.count(JobScan.id))
    if risk_level:
        stmt = stmt.where(JobScan.risk_level == risk_level)
    return int(db.execute(stmt).scalar_one())


def recent_scans(db: Session, limit: int = 5) -> Sequence[JobScan]:
    return list_scans(db, limit=limit)


# ---------------------------------------------------------------------------
# Aggregates (dashboard)
# ---------------------------------------------------------------------------
def statistics(db: Session) -> Dict[str, Any]:
    """
    Aggregated dashboard metrics, computed entirely in SQL.

    Returns both the verbose tier names the UI compares against and the percentage
    distribution used for the donut chart.
    """
    total = count_scans(db)
    counts = {
        level: count_scans(db, level) for level in RISK_LEVELS
    }
    avg_score = db.execute(select(func.avg(JobScan.risk_score))).scalar_one()

    genuine = int(db.execute(
        select(func.count(JobScan.id)).where(JobScan.ml_prediction == "Genuine")
    ).scalar_one())
    suspicious = int(db.execute(
        select(func.count(JobScan.id)).where(JobScan.ml_prediction == "Fraudulent")
    ).scalar_one())

    distribution = {
        level: {
            "count": counts[level],
            "percentage": round((counts[level] / total) * 100, 1) if total else 0.0,
        }
        for level in RISK_LEVELS
    }

    return {
        "total_scans": total,
        "genuine_count": genuine,
        "suspicious_count": suspicious,
        "low_risk_count": counts[LOW],
        "medium_risk_count": counts[MEDIUM],
        "high_risk_count": counts[HIGH],
        "average_risk_score": round(float(avg_score), 1) if avg_score is not None else 0.0,
        "risk_distribution": distribution,
        "top_flags": top_flags(db, limit=5),
        "trend": daily_trend(db, days=7),
    }


def top_flags(db: Session, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Most frequently triggered heuristic flags.

    The flags live in a JSON column, which SQLite cannot group on, so the counting is
    done in Python over the stored lists.
    """
    tally: Dict[str, Dict[str, Any]] = {}
    for flags in db.execute(select(JobScan.detected_flags)).scalars():
        for flag in flags or []:
            name = flag.get("flag") or flag.get("title") or flag.get("id")
            if not name:
                continue
            entry = tally.setdefault(name, {"flag": name, "count": 0,
                                            "severity": flag.get("severity", "MEDIUM")})
            entry["count"] += 1
    ranked = sorted(tally.values(), key=lambda item: item["count"], reverse=True)
    return ranked[:limit]


def daily_trend(db: Session, days: int = 7) -> List[Dict[str, Any]]:
    """Scan volume per day, oldest first, zero-filled so charts never have gaps."""
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=days - 1)

    rows = db.execute(
        select(func.date(JobScan.created_at).label("day"), func.count(JobScan.id))
        .where(JobScan.created_at >= datetime.combine(start, datetime.min.time(), timezone.utc))
        .group_by("day")
    ).all()
    by_day = {str(row[0]): int(row[1]) for row in rows}

    return [
        {"date": (start + timedelta(days=offset)).isoformat(),
         "count": by_day.get((start + timedelta(days=offset)).isoformat(), 0)}
        for offset in range(days)
    ]


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------
def delete_scan(db: Session, scan_id: int) -> bool:
    scan = db.get(JobScan, scan_id)
    if scan is None:
        return False
    db.delete(scan)
    db.commit()
    return True


def delete_all_scans(db: Session) -> int:
    deleted = db.query(JobScan).delete()
    db.commit()
    return int(deleted or 0)
