"""Pydantic schemas for history and dashboard responses."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ScanSummary(BaseModel):
    """
    One row in GET /api/history.

    Field names match what the existing React components read (`job_text`,
    `prediction`, `warnings`, `warning_count`, `timestamp`), so the UI needed no change
    when this schema was introduced.
    """

    model_config = ConfigDict(extra="allow")

    id: int
    timestamp: str
    created_at: Optional[str] = None
    job_title: str = ""
    company_name: str = ""
    job_text: str = ""
    salary: str = ""
    contact_email: str = ""
    prediction: str
    ml_prediction: str = ""
    ml_probability: float = 0.0
    risk_score: int
    risk_level: str
    rule_score: int = 0
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    warning_count: int = 0
    recommendations: List[str] = Field(default_factory=list)
    score_breakdown: Dict[str, Any] = Field(default_factory=dict)
    source_type: str = "text"
    source_url: str = ""


class HistoryStats(BaseModel):
    """Response of GET /api/history/stats."""

    total_scans: int
    low_risk_count: int
    medium_risk_count: int
    high_risk_count: int
    average_risk_score: float
    genuine_count: int = 0
    suspicious_count: int = 0


class RiskDistribution(BaseModel):
    count: int
    percentage: float


class DashboardResponse(BaseModel):
    """
    Response of GET /api/dashboard.

    Contains every number the dashboard cards, the donut chart, the flag breakdown and
    the recent-activity table need — all computed in SQL from `job_scans`.
    """

    total_scans: int
    genuine_count: int
    suspicious_count: int
    low_risk_count: int
    medium_risk_count: int
    high_risk_count: int
    average_risk_score: float
    risk_distribution: Dict[str, RiskDistribution]
    top_flags: List[Dict[str, Any]]
    trend: List[Dict[str, Any]]
    recent_scans: List[ScanSummary]


class DeleteResponse(BaseModel):
    success: bool
    message: str = ""
    deleted_id: Optional[int] = None


class HealthResponse(BaseModel):
    """Response of GET /api/health."""

    status: str
    environment: str
    version: str
    model_ready: bool
    model_error: Optional[str] = None
    database: Dict[str, Any]
    ollama: Dict[str, Any]
    rules_loaded: int
