"""
Health endpoints.

    GET /api/health       liveness + dependency readiness (model, database, Ollama)
    GET /api/model        model metadata and evaluation metrics
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from backend.api.schemas.history_schema import HealthResponse
from backend.config import settings
from backend.database.connection import health as db_health
from backend.services import ml_service as ml_module
from backend.services.explanation_service import get_explanation_service
from backend.services.rule_engine import get_rule_engine

router = APIRouter(prefix="/api", tags=["health"])


def _ml() -> Any:
    """Reuses the single MLService instance owned by the scan pipeline."""
    from backend.services.scan_service import get_scan_service

    return get_scan_service().ml


@router.get("/health", response_model=HealthResponse, summary="Backend health")
def health() -> Dict[str, Any]:
    """
    Reports backend liveness plus the state of every dependency.

    `status` is "ok" when the core (model loaded, database readable) is healthy, and
    "degraded" when the app can serve requests but a dependency is unavailable.
    Ollama is optional and never affects `status`.
    """
    database = db_health()
    model = _ml()
    explanation = get_explanation_service()
    ollama_online = explanation.is_available()

    core_ok = database.get("ok", False) and model.is_ready

    return {
        "status": "ok" if core_ok else "degraded",
        "environment": settings.environment,
        "version": settings.app_version,
        "model_ready": model.is_ready,
        "model_error": model.load_error,
        "database": database,
        "ollama": {
            "available": ollama_online,
            "url": explanation.base_url,
            "models": explanation.list_models() if ollama_online else [],
            "note": "Optional. Explanations only; never affects scoring.",
        },
        "rules_loaded": len(get_rule_engine().rules),
    }


@router.get("/model", summary="Model metadata and evaluation metrics")
def model_info() -> Dict[str, Any]:
    """Held-out evaluation metrics recorded at training time."""
    return _ml().info()
