"""
Scan orchestration service.

This is the one place the full pipeline is sequenced:

    validate -> aggregate text -> ML inference -> rule engine
             -> risk blend (+ floors) -> recommendations
             -> persist to SQLite -> optional Ollama narrative

Routers call this; they contain no business logic of their own.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import crud
from backend.database.models import JobScan
from backend.services.explanation_service import ExplanationService, get_explanation_service
from backend.services.ml_service import MLService
from backend.services.risk_analyzer import RiskAnalyzer
from backend.services.rule_engine import RuleEngine, get_rule_engine

logger = logging.getLogger(__name__)


class ScanInputError(ValueError):
    """Raised when the submitted advertisement cannot be analysed."""


@dataclass
class ScanInput:
    """Everything needed to analyse one advertisement."""

    job_description: str
    job_title: str = ""
    company_name: str = ""
    salary: str = ""
    contact_email: str = ""
    #: Extra free-text context (skills, application instructions).
    extra: str = ""
    source_type: str = "text"
    source_url: str = ""
    model_name: Optional[str] = None
    include_ai_explanation: bool = False

    def aggregated_text(self) -> str:
        """
        Builds the text handed to the ML model.

        The ordering mirrors the training data (title, company, description, then
        metadata) so the learned TF-IDF vocabulary matches what inference sees.
        """
        parts = [
            self.job_title.strip(),
            self.company_name.strip(),
            self.job_description.strip(),
            self.extra.strip(),
            self.salary.strip(),
        ]
        return " ".join(part for part in parts if part)


@dataclass
class ScanOutcome:
    """Result of a scan, ready to be serialised by the router."""

    scan: Optional[JobScan]
    payload: Dict[str, Any] = field(default_factory=dict)


class ScanService:
    """Owns the detection pipeline and the singletons it depends on."""

    def __init__(
        self,
        ml_service: Optional[MLService] = None,
        rule_engine: Optional[RuleEngine] = None,
        risk_analyzer: Optional[RiskAnalyzer] = None,
        explanation_service: Optional[ExplanationService] = None,
    ) -> None:
        self.ml = ml_service or MLService()
        self.rules = rule_engine or get_rule_engine()
        self.risk = risk_analyzer or RiskAnalyzer()
        self.explanations = explanation_service or get_explanation_service()

    # ------------------------------------------------------------------
    def analyse(self, data: ScanInput) -> Dict[str, Any]:
        """
        Runs the pipeline without persistence.

        Useful for previews and tests; `execute` wraps this and saves the row.
        """
        description = (data.job_description or "").strip()
        if not description:
            raise ScanInputError("Job description is required to analyse a posting.")
        if len(description) > settings.max_description_chars:
            raise ScanInputError(
                f"Job description is too long ({len(description)} characters). "
                f"Maximum is {settings.max_description_chars}."
            )

        # 1. ML inference
        ml_result = self.ml.predict(data.aggregated_text())

        # 2. Heuristic rules. The engine also inspects the contact address and, for
        #    URL sources, the domain (look-alike domains are a real attack vector).
        heuristic_text = " ".join(part for part in (
            data.job_description,
            data.salary,
            data.contact_email,
            data.extra,
        ) if part)
        rule_result = self.rules.analyze(heuristic_text, company=data.company_name)

        # 3. Blended risk with safety floors
        risk_result = self.risk.analyze(ml_result, rule_result)

        # 4. Recommendations
        recommendations = self.explanations.recommendations(
            risk_result["risk_level"], risk_result["flags"]
        )

        return {
            "ml_result": ml_result,
            "rule_result": rule_result,
            "risk_result": risk_result,
            "recommendations": recommendations,
        }

    # ------------------------------------------------------------------
    def execute(self, db: Session, data: ScanInput) -> Dict[str, Any]:
        """Runs the pipeline, persists the row, and returns the API payload."""
        analysis = self.analyse(data)
        ml_result = analysis["ml_result"]
        risk_result = analysis["risk_result"]

        ai_explanation = None
        if data.include_ai_explanation:
            ai_explanation = self.explanations.explain(
                job_title=data.job_title or "Job advertisement",
                company=data.company_name or "Not stated",
                risk_level=risk_result["risk_level"],
                risk_score=risk_result["risk_score"],
                flags=risk_result["flags"],
                model_name=data.model_name,
            )

        storage_warning = None
        scan: Optional[JobScan] = None
        try:
            scan = crud.create_scan(
                db,
                job_title=(data.job_title or "").strip(),
                company_name=(data.company_name or "").strip(),
                job_description=data.job_description.strip(),
                salary=(data.salary or "").strip(),
                contact_email=(data.contact_email or "").strip(),
                prediction=risk_result["prediction"],
                ml_prediction=ml_result.get("prediction_label", "Unknown"),
                ml_probability=float(ml_result.get("fraud_probability") or 0.0),
                risk_score=risk_result["risk_score"],
                risk_level=risk_result["risk_level"],
                rule_score=risk_result["rule_score"],
                detected_flags=risk_result["flags"],
                recommendations=analysis["recommendations"],
                score_breakdown=risk_result["score_breakdown"],
                source_type=data.source_type,
                source_url=data.source_url,
            )
        except Exception as exc:  # a storage failure must never discard a verdict
            logger.exception("Failed to persist scan")
            db.rollback()
            storage_warning = f"Audit record could not be saved: {exc}"

        return self.build_response(
            data=data,
            analysis=analysis,
            scan=scan,
            ai_explanation=ai_explanation,
            storage_warning=storage_warning,
        )

    # ------------------------------------------------------------------
    @staticmethod
    def build_response(
        *,
        data: ScanInput,
        analysis: Dict[str, Any],
        scan: Optional[JobScan],
        ai_explanation: Optional[Dict[str, Any]] = None,
        storage_warning: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Assembles the response consumed by the React UI.

        The UI reads `risk_result.risk_level` against the strings "Low Risk" /
        "Medium Risk" / "High Risk", `risk_result.warnings`, `ml_result.fraud_score_pct`
        and `ml_result.genuine_probability`, so those shapes are preserved exactly while
        the new nested detail (score_breakdown, flags, evidence) is added alongside.
        """
        ml_result = analysis["ml_result"]
        risk_result = analysis["risk_result"]
        recommendations = analysis["recommendations"]

        payload: Dict[str, Any] = {
            "success": True,
            "scan_id": scan.id if scan else None,
            # ---- Spec-level summary fields -------------------------------
            "prediction": risk_result["prediction"],
            "risk_score": risk_result["risk_score"],
            "risk_level": risk_result["risk_level"],
            "ml_prediction": ml_result.get("prediction_label"),
            "ml_probability": ml_result.get("fraud_probability"),
            "rule_based_flags": risk_result["flags"],
            "recommendations": recommendations,
            "explanation": risk_result["explanation"],
            "score_breakdown": risk_result["score_breakdown"],
            # ---- Existing UI contract ------------------------------------
            "job_title": data.job_title or "Unspecified Title",
            "company_name": data.company_name or "Unspecified Employer",
            "salary_info": data.salary,
            "contact_email": data.contact_email,
            "job_description": data.job_description,
            "source_type": data.source_type,
            "source_url": data.source_url,
            "ml_result": ml_result,
            "rule_result": {
                "warnings": risk_result["flags"],
                "warning_count": len(risk_result["flags"]),
                "rule_score": risk_result["rule_score"],
                "rules_evaluated": analysis["rule_result"]["rules_evaluated"],
            },
            "risk_result": risk_result,
            "safety_tips": recommendations,
            "ai_explanation": ai_explanation,
        }
        if storage_warning:
            payload["storage_warning"] = storage_warning
        return payload


_service: Optional[ScanService] = None


def get_scan_service() -> ScanService:
    global _service
    if _service is None:
        _service = ScanService()
    return _service
