"""
Service layer for JobShield AI.

This module owns the single authoritative detection pipeline. Both the FastAPI
service (`api.py`) and the Streamlit app (`app.py`) call into it, so the ML model,
heuristic rules, risk blending and safety advice can never drift between surfaces.

Pipeline:
    raw input (text / url / image)
        -> text aggregation
        -> TF-IDF + Logistic Regression  (probabilistic engine)
        -> 8-rule heuristic scanner      (deterministic engine)
        -> ensemble risk blend + CRITICAL safety floor
        -> safety recommendations
        -> SQLite audit trail
        -> optional local Ollama narrative
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from database.db_manager import DatabaseManager
from model.predictor import JobPredictor
from utils.detector import ScamDetector
from utils.explanation import get_safety_recommendations
from utils.ollama_client import OllamaClient
from utils.risk_analyzer import RiskAnalyzer
from utils.url_fetcher import UrlFetchError, fetch_url_text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

#: Extra words the heuristic engine should also see when a posting is fetched from a
#: URL (host name plus the path words help catch look-alike domains).
MAX_INPUT_CHARS = 20000


class InputError(ValueError):
    """Raised when caller-supplied input cannot be analysed."""


@dataclass
class ScanPayload:
    """Normalised scan request, independent of the transport that delivered it."""

    job_description: str
    job_title: str = ""
    company_name: str = ""
    salary_info: str = ""
    contact_email: str = ""
    instructions: str = ""
    skills: str = ""
    source_url: Optional[str] = None
    source_type: str = "text"  # text | url | image
    ollama_model: str = "llama3.2:latest"
    include_ai_explanation: bool = False
    persist: bool = True


@dataclass
class ScanResult:
    """Everything the UI layers need to render a verdict."""

    scan_id: Optional[int]
    payload: ScanPayload
    ml_result: Dict[str, Any]
    rule_result: Dict[str, Any]
    risk_result: Dict[str, Any]
    safety_tips: List[str]
    ai_explanation: Optional[Dict[str, Any]] = None
    extracted: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scan_id": self.scan_id,
            "job_title": self.payload.job_title or "Unspecified Title",
            "company_name": self.payload.company_name or "Unspecified Employer",
            "salary_info": self.payload.salary_info,
            "contact_email": self.payload.contact_email,
            "job_description": self.payload.job_description,
            "source_url": self.payload.source_url,
            "source_type": self.payload.source_type,
            "extracted": self.extracted,
            "ml_result": self.ml_result,
            "rule_result": self.rule_result,
            "risk_result": self.risk_result,
            "safety_tips": self.safety_tips,
            "ai_explanation": self.ai_explanation,
        }


def _clean(text: Optional[str]) -> str:
    return (text or "").strip()


class DetectionService:
    """Process-wide singleton wrapper around model, rules, risk engine and database."""

    def __init__(self, model_dir: Optional[str] = None, db_path: Optional[str] = None) -> None:
        self.model_dir = model_dir or os.path.join(BASE_DIR, "saved_models")
        self.db = DatabaseManager(db_path) if db_path else DatabaseManager()
        self.predictor = JobPredictor(model_dir=self.model_dir)
        self.detector = ScamDetector()
        self.analyzer = RiskAnalyzer()
        self.ollama = OllamaClient()

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
    def status(self) -> Dict[str, Any]:
        ollama_online = self.ollama.is_available()
        discovered = self.ollama.list_models() if ollama_online else []
        return {
            "status": "online",
            "service": "JobShield AI Core",
            "ml_ready": self.predictor.is_ready,
            "ollama_available": ollama_online,
            "ollama_models": discovered,
            # When Ollama is offline we still advertise the models the user could pull,
            # but `ollama_available` is what the UI keys its badge off.
            "suggested_ollama_models": ["llama3.2:latest", "gemma2:2b", "mistral"],
            "active_ollama_model": self.ollama.model_name,
            "rules_loaded": len(self.detector.rules),
            "rule_ids": [rule["id"] for rule in self.detector.rules],
        }

    def statistics(self) -> Dict[str, Any]:
        return self.db.get_statistics()

    def history(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self.db.get_recent_scans(limit=limit)

    # ------------------------------------------------------------------
    # Input extraction helpers
    # ------------------------------------------------------------------
    @staticmethod
    def fetch_from_url(url: str) -> Dict[str, Any]:
        try:
            return fetch_url_text(url)
        except UrlFetchError as exc:
            raise InputError(str(exc)) from exc

    @staticmethod
    def ocr_image(data: bytes, language: str = "eng") -> Dict[str, Any]:
        """Extracts text from an uploaded screenshot using Tesseract."""
        try:
            import pytesseract  # noqa: WPS433 (optional dependency)
            from PIL import Image
        except ImportError as exc:  # pragma: no cover - optional extra
            raise InputError(
                "OCR support is not installed. Run `pip install pillow pytesseract` "
                "and install the Tesseract binary for your platform."
            ) from exc

        try:
            image = Image.open(io.BytesIO(data))
        except Exception as exc:
            raise InputError("Uploaded file is not a readable image.") from exc

        try:
            text = pytesseract.image_to_string(image, lang=language)
        except pytesseract.TesseractNotFoundError as exc:
            raise InputError(
                "Tesseract OCR binary not found on PATH. Install it from "
                "https://github.com/tesseract-ocr/tesseract and retry."
            ) from exc
        except Exception as exc:
            raise InputError(f"OCR failed: {exc}") from exc

        text = (text or "").strip()
        if not text:
            raise InputError("OCR produced no readable text. Try a higher-resolution screenshot.")
        return {"text": text, "width": image.width, "height": image.height, "language": language}

    @staticmethod
    def domain_of(url: str) -> str:
        netloc = urlparse(url if "://" in url else f"https://{url}").netloc.lower()
        return netloc[4:] if netloc.startswith("www.") else netloc

    # ------------------------------------------------------------------
    # Core pipeline
    # ------------------------------------------------------------------
    def scan(self, payload: ScanPayload) -> ScanResult:
        if not _clean(payload.job_description):
            raise InputError("Job advertisement text is required for analysis.")

        description = _clean(payload.job_description)[:MAX_INPUT_CHARS]

        # Aggregated text for the ML engine, mirroring model/train_model.py:prepare_text.
        # Metadata is appended after the posting body so keyword context is preserved.
        aggregated_text = " ".join(
            part
            for part in (
                _clean(payload.job_title),
                _clean(payload.company_name),
                description,
                _clean(payload.salary_info),
                _clean(payload.skills),
                _clean(payload.instructions),
            )
            if part
        )

        # The heuristic engine additionally inspects the contact surface and, for URL
        # sources, the host name (look-alike domains are a real scam vector).
        heuristic_parts = [
            _clean(payload.salary_info),
            _clean(payload.contact_email),
            _clean(payload.instructions),
            description,
        ]
        if payload.source_url:
            heuristic_parts.append(self.domain_of(payload.source_url))
        heuristic_text = " ".join(part for part in heuristic_parts if part)

        ml_result = self.predictor.predict(aggregated_text)
        rule_result = self.detector.analyze(text=heuristic_text, company=_clean(payload.company_name))
        risk_result = self.analyzer.calculate_risk(ml_result, rule_result)
        safety_tips = get_safety_recommendations(risk_result["risk_level"], risk_result["warnings"])

        scan_id: Optional[int] = None
        if payload.persist:
            scan_id = self.db.save_scan(
                job_text=description,
                prediction=risk_result["verdict"],
                risk_score=risk_result["risk_score"],
                risk_level=risk_result["risk_level"],
                job_title=_clean(payload.job_title) or "Unspecified Title",
                company_name=_clean(payload.company_name) or "Unspecified Employer",
                warnings=risk_result["warnings"],
                source_url=payload.source_url or "",
                source_type=payload.source_type,
            )

        ai_explanation = None
        if payload.include_ai_explanation:
            if payload.ollama_model:
                self.ollama.model_name = payload.ollama_model
            ai_explanation = self.ollama.generate_explanation(
                job_title=_clean(payload.job_title) or "Job Advertisement",
                company=_clean(payload.company_name) or "Not specified",
                risk_score=risk_result["risk_score"],
                risk_level=risk_result["risk_level"],
                warnings=risk_result["warnings"],
            )

        return ScanResult(
            scan_id=scan_id,
            payload=payload,
            ml_result=ml_result,
            rule_result=rule_result,
            risk_result=risk_result,
            safety_tips=safety_tips,
            ai_explanation=ai_explanation,
            extracted={"source_type": payload.source_type, "source_url": payload.source_url},
        )

    # ------------------------------------------------------------------
    # History management
    # ------------------------------------------------------------------
    def delete_scan(self, scan_id: int) -> bool:
        return self.db.delete_scan(scan_id)

    def clear_history(self) -> bool:
        return self.db.clear_all_history()

    def explain(self, *, job_title: str, company_name: str, risk_score: int, risk_level: str,
                warnings: List[Dict[str, Any]], model_name: Optional[str] = None) -> Dict[str, Any]:
        if model_name:
            self.ollama.model_name = model_name
        return self.ollama.generate_explanation(
            job_title=job_title or "Job Advertisement",
            company=company_name or "Not specified",
            risk_score=risk_score,
            risk_level=risk_level,
            warnings=warnings,
        )


_service: Optional[DetectionService] = None


def get_service() -> DetectionService:
    """Returns the lazily created process-wide detection service."""
    global _service
    if _service is None:
        _service = DetectionService()
    return _service
