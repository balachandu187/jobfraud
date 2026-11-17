"""
Dashboard endpoint.

    GET /api/dashboard   everything the dashboard cards, charts and recent-activity
                         table need, in one round trip.

Also keeps the two legacy aggregate paths (`/api/stats`, `/api/status`) that the
existing React app calls, so the UI needs no change.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.schemas.history_schema import DashboardResponse
from backend.database import crud
from backend.database.connection import get_db
from backend.services.explanation_service import get_explanation_service
from backend.services.ml_service import MLService
from backend.services.rule_engine import get_rule_engine

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse, summary="Dashboard metrics")
def get_dashboard(
    recent_limit: int = Query(6, ge=1, le=50, description="How many recent scans to include"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns totals, per-tier counts, percentages, top triggered flags, a 7-day trend and
    the most recent scans. Every number is aggregated from the `job_scans` table.
    """
    stats = crud.statistics(db)
    recent = crud.recent_scans(db, limit=recent_limit)
    stats["recent_scans"] = [scan.to_history_dict() for scan in recent]
    return stats


@router.get("/stats", summary="Legacy aggregate stats (used by the current UI)")
def get_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Flat metrics shape consumed by the existing dashboard cards."""
    stats = crud.statistics(db)
    return {
        "total_scans": stats["total_scans"],
        "low_risk_count": stats["low_risk_count"],
        "medium_risk_count": stats["medium_risk_count"],
        "high_risk_count": stats["high_risk_count"],
        "average_risk_score": stats["average_risk_score"],
        "genuine_count": stats["genuine_count"],
        "suspicious_count": stats["suspicious_count"],
        "top_warnings": [
            {"title": item["flag"], "count": item["count"]} for item in stats["top_flags"]
        ],
        "trend_7d": stats["trend"],
    }


@router.get("/status", summary="Engine telemetry (used by the current UI)")
def get_status() -> Dict[str, Any]:
    """ML readiness, Ollama availability and the loaded rule set."""
    from backend.database.connection import health as db_health

    ml = MLService()  # singleton below; this keeps the endpoint dependency-free
    explanation = get_explanation_service()
    ollama_online = explanation.is_available()
    models = explanation.list_models() if ollama_online else []

    return {
        "status": "online",
        "service": "JobShield AI Core",
        "ml_ready": get_ml().is_ready,
        "ollama_available": ollama_online,
        "ollama_models": models,
        "suggested_ollama_models": ["llama3.2:latest", "gemma2:2b", "mistral"],
        "active_ollama_model": explanation.model_name,
        "storage": db_health(),
        "rules_loaded": len(get_rule_engine().rules),
        "rule_ids": [rule.id for rule in get_rule_engine().rules],
    }


_ml_singleton: MLService | None = None


def get_ml() -> MLService:
    """Shares the process-wide MLService with the scan pipeline (single model load)."""
    global _ml_singleton
    if _ml_singleton is None:
        from backend.services.scan_service import get_scan_service

        _ml_singleton = get_scan_service().ml
    return _ml_singleton
