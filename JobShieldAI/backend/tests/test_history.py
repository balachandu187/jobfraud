"""
Tests for the history, dashboard and health endpoints.

Covers: listing, filtering, search, pagination, single-record fetch, deletion,
aggregate statistics, dashboard payload, health reporting and the UI field contract.
"""

from __future__ import annotations

import pytest

from backend.database import crud


def _seed(client, texts: list[str]) -> list[int]:
    ids = []
    for text in texts:
        response = client.post("/api/scan", json={"job_description": text, "company_name": "Acme Ltd"})
        assert response.status_code == 200, response.text
        ids.append(response.json()["scan_id"])
    return ids


SCAM = "Pay a registration fee of 2000. No interview required. Contact HR on Telegram."
GENUINE = (
    "We are hiring a backend engineer with strong Python and PostgreSQL skills. "
    "Candidates complete two technical interviews and a coding assessment via our portal."
)


# ---------------------------------------------------------------------------
# History listing
# ---------------------------------------------------------------------------
def test_history_is_empty_initially(client):
    assert client.get("/api/history").json() == []


def test_history_returns_newest_first(client):
    ids = _seed(client, [SCAM, GENUINE])
    rows = client.get("/api/history").json()
    assert [row["id"] for row in rows] == list(reversed(ids))


def test_history_row_satisfies_the_frontend_contract(client):
    """The React UI reads these exact keys — losing one blanks the history page."""
    _seed(client, [SCAM])
    row = client.get("/api/history").json()[0]
    for key in ("id", "timestamp", "job_title", "company_name", "job_text",
                "prediction", "risk_score", "risk_level", "warnings", "warning_count"):
        assert key in row, f"missing frontend field: {key}"
    # The UI compares risk_level against these exact strings.
    assert row["risk_level"] in ("Low Risk", "Medium Risk", "High Risk")
    assert isinstance(row["warnings"], list)


def test_history_filter_by_risk_level(client):
    _seed(client, [SCAM, GENUINE])
    high = client.get("/api/history", params={"risk_level": "High Risk"}).json()
    low = client.get("/api/history", params={"risk_level": "Low Risk"}).json()
    assert len(high) == 1 and len(low) == 1
    assert high[0]["risk_level"] == "High Risk"


def test_history_rejects_invalid_risk_level(client):
    response = client.get("/api/history", params={"risk_level": "Critical"})
    assert response.status_code == 400


def test_history_search_matches_title_and_text(client):
    client.post("/api/scan", json={"job_description": SCAM, "job_title": "Data Entry Operator"})
    client.post("/api/scan", json={"job_description": GENUINE, "job_title": "Backend Engineer"})
    assert len(client.get("/api/history", params={"search": "Data Entry"}).json()) == 1
    assert len(client.get("/api/history", params={"search": "Telegram"}).json()) == 1
    assert len(client.get("/api/history", params={"search": "nothing-here"}).json()) == 0


def test_history_pagination(client):
    _seed(client, [SCAM] * 3)
    first = client.get("/api/history", params={"limit": 2}).json()
    second = client.get("/api/history", params={"limit": 2, "offset": 2}).json()
    assert len(first) == 2 and len(second) == 1
    assert {row["id"] for row in first}.isdisjoint({row["id"] for row in second})


def test_history_rejects_bad_pagination(client):
    assert client.get("/api/history", params={"limit": 0}).status_code == 422
    assert client.get("/api/history", params={"limit": 10_000}).status_code == 422


# ---------------------------------------------------------------------------
# Single record
# ---------------------------------------------------------------------------
def test_get_single_scan(client):
    scan_id = _seed(client, [SCAM])[0]
    body = client.get(f"/api/history/{scan_id}").json()
    assert body["id"] == scan_id
    assert body["job_text"] == SCAM
    assert body["recommendations"]
    assert body["score_breakdown"]


def test_get_missing_scan_returns_404(client):
    response = client.get("/api/history/999999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_history_stats_route_is_not_shadowed_by_scan_id(client):
    """Regression: /api/history/stats must not be parsed as /api/history/{scan_id}."""
    response = client.get("/api/history/stats")
    assert response.status_code == 200
    assert "total_scans" in response.json()


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------
def test_delete_single_scan(client):
    scan_id = _seed(client, [SCAM, GENUINE])[0]
    assert client.delete(f"/api/history/{scan_id}").json()["success"] is True
    assert client.get(f"/api/history/{scan_id}").status_code == 404
    assert len(client.get("/api/history").json()) == 1


def test_delete_missing_scan_returns_404(client):
    assert client.delete("/api/history/999999").status_code == 404


def test_delete_all_scans(client):
    _seed(client, [SCAM, GENUINE, SCAM])
    assert client.delete("/api/history").json()["success"] is True
    assert client.get("/api/history").json() == []


# ---------------------------------------------------------------------------
# Statistics and dashboard
# ---------------------------------------------------------------------------
def test_history_stats_counts_each_tier(client):
    _seed(client, [SCAM, GENUINE])
    stats = client.get("/api/history/stats").json()
    assert stats["total_scans"] == 2
    assert stats["high_risk_count"] == 1
    assert stats["low_risk_count"] == 1
    assert stats["high_risk_count"] + stats["medium_risk_count"] + stats["low_risk_count"] == 2
    assert stats["average_risk_score"] >= 0


def test_dashboard_payload_is_complete(client):
    _seed(client, [SCAM, GENUINE])
    body = client.get("/api/dashboard").json()
    for key in ("total_scans", "genuine_count", "suspicious_count", "low_risk_count",
                "medium_risk_count", "high_risk_count", "average_risk_score",
                "risk_distribution", "top_flags", "trend", "recent_scans"):
        assert key in body, f"missing dashboard field: {key}"
    assert len(body["trend"]) == 7
    assert body["recent_scans"]
    distribution = body["risk_distribution"]
    assert set(distribution) == {"Low Risk", "Medium Risk", "High Risk"}
    assert distribution["High Risk"]["count"] == 1


def test_dashboard_distribution_percentages_sum_to_100(client):
    _seed(client, [SCAM, GENUINE, GENUINE])
    distribution = client.get("/api/dashboard").json()["risk_distribution"]
    total = sum(item["percentage"] for item in distribution.values())
    assert 99.0 <= total <= 101.0   # rounding across three buckets


def test_dashboard_top_flags_counts_repeated_rules(client):
    _seed(client, [SCAM, SCAM])
    flags = client.get("/api/dashboard").json()["top_flags"]
    assert flags
    assert max(item["count"] for item in flags) == 2


def test_dashboard_is_empty_safe(client):
    body = client.get("/api/dashboard").json()
    assert body["total_scans"] == 0
    assert body["average_risk_score"] == 0.0
    assert body["risk_distribution"]["High Risk"]["percentage"] == 0.0


# ---------------------------------------------------------------------------
# Legacy endpoints the current UI calls
# ---------------------------------------------------------------------------
def test_legacy_stats_shape(client):
    _seed(client, [SCAM])
    body = client.get("/api/stats").json()
    for key in ("total_scans", "low_risk_count", "medium_risk_count", "high_risk_count",
                "average_risk_score", "top_warnings", "trend_7d"):
        assert key in body
    # The dashboard renders `title`; the new API calls it `flag`.
    assert {"title", "count"} <= set(body["top_warnings"][0])


def test_legacy_status_shape(client):
    body = client.get("/api/status").json()
    for key in ("ml_ready", "ollama_available", "rules_loaded", "rule_ids", "storage"):
        assert key in body


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
def test_health_reports_dependencies(client):
    body = client.get("/api/health").json()
    assert body["status"] in ("ok", "degraded")
    assert body["model_ready"] is True
    assert body["database"]["ok"] is True
    assert body["ollama"]["available"] in (True, False)
    assert body["rules_loaded"] >= 10


def test_health_degrades_without_model(client, monkeypatch):
    """A missing model must be reported, not hidden behind a green light."""
    from backend.services import scan_service as scan_module
    from backend.services.ml_service import MLService

    service = scan_module.get_scan_service()
    original_ml = service.ml
    original_factory = scan_module.get_scan_service

    # Swap in an unavailable MLService for the duration of the request.
    blind = MLService(model_dir="/nonexistent-model-dir")
    service.ml = blind
    try:
        body = client.get("/api/health").json()
        assert body["model_ready"] is False
        assert body["model_error"]
        assert body["status"] == "degraded"
    finally:
        service.ml = original_ml
        assert original_factory is scan_module.get_scan_service


def test_model_endpoint_exposes_metrics(client):
    body = client.get("/api/model").json()
    assert body["ready"] is True
    assert "metrics" in body


# ---------------------------------------------------------------------------
# CRUD layer directly
# ---------------------------------------------------------------------------
def test_crud_search_is_case_insensitive(db_session):
    crud.create_scan(
        db_session,
        job_title="Data ENTRY Clerk", company_name="Acme", job_description="text " * 40,
        prediction="Suspicious", ml_prediction="Fraudulent", ml_probability=0.8,
        risk_score=50, risk_level="Medium Risk", rule_score=20,
    )
    assert len(crud.list_scans(db_session, search="data entry")) == 1
    assert len(crud.list_scans(db_session, search="DATA ENTRY")) == 1


def test_crud_counts_match_filters(db_session):
    for level, score in (("Low Risk", 10), ("High Risk", 90), ("High Risk", 80)):
        crud.create_scan(
            db_session, job_title="t", company_name="c", job_description="d" * 50,
            prediction="p", ml_prediction="Genuine", ml_probability=0.1,
            risk_score=score, risk_level=level, rule_score=0,
        )
    assert crud.count_scans(db_session) == 3
    assert crud.count_scans(db_session, "High Risk") == 2
    assert crud.statistics(db_session)["average_risk_score"] == 60.0
