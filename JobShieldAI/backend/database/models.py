"""
SQLAlchemy ORM models for JobShield AI.

`JobScan` is the single persistent entity: one row per analysed advertisement, with the
ML verdict, rule flags, recommendations and provenance stored alongside the input.

JSON-shaped columns use SQLAlchemy's `JSON` type, which SQLite stores as TEXT and
serialises/deserialises automatically — so callers work with plain Python lists/dicts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, Float, Index, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Timezone-aware UTC timestamp (datetime.utcnow is deprecated in 3.12+)."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class JobScan(Base):
    """A single job-advertisement analysis."""

    __tablename__ = "job_scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    # ---- Input ------------------------------------------------------
    job_title: Mapped[Optional[str]] = mapped_column(String(300), default="")
    company_name: Mapped[Optional[str]] = mapped_column(String(300), default="")
    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    salary: Mapped[Optional[str]] = mapped_column(String(200), default="")
    contact_email: Mapped[Optional[str]] = mapped_column(String(320), default="")

    # ---- Verdict ----------------------------------------------------
    prediction: Mapped[str] = mapped_column(String(60), nullable=False)
    ml_prediction: Mapped[str] = mapped_column(String(40), nullable=False)
    ml_probability: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    #: One of "Low Risk" | "Medium Risk" | "High Risk" (kept verbose to match the UI).
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    rule_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ---- Detail (JSON) ----------------------------------------------
    detected_flags: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    recommendations: Mapped[List[str]] = mapped_column(JSON, default=list)
    #: 0-100 contribution of each engine plus any enforced safety floor.
    score_breakdown: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    # ---- Provenance -------------------------------------------------
    source_type: Mapped[str] = mapped_column(String(20), default="text")
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), default="")

    __table_args__ = (
        Index("ix_job_scans_risk_level_created", "risk_level", "created_at"),
    )

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------
    def to_history_dict(self) -> Dict[str, Any]:
        """
        Shape expected by the existing React UI.

        The frontend reads `job_text`, `prediction`, `warnings` and `warning_count`,
        so those aliases are provided here rather than leaking the new schema into the UI.
        """
        flags = self.detected_flags or []
        return {
            "id": self.id,
            "timestamp": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "job_title": self.job_title or "",
            "company_name": self.company_name or "",
            "job_text": self.job_description,
            "salary": self.salary or "",
            "contact_email": self.contact_email or "",
            "prediction": self.prediction,
            "ml_prediction": self.ml_prediction,
            "ml_probability": self.ml_probability,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "rule_score": self.rule_score,
            "warnings": flags,
            "warning_count": len(flags),
            "recommendations": self.recommendations or [],
            "score_breakdown": self.score_breakdown or {},
            "source_type": self.source_type or "text",
            "source_url": self.source_url or "",
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<JobScan id={self.id} risk={self.risk_score} level={self.risk_level!r}>"
