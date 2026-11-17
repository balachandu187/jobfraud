"""
Scan endpoints.

    POST /api/scan          analyse supplied text
    POST /api/scan/url      fetch a public URL, extract text, analyse
    POST /api/scan/image    OCR an uploaded screenshot, analyse
    POST /api/scan/explain  optional Ollama narrative for an existing verdict
    GET  /api/rules         heuristic catalogue (documentation)
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.api.schemas.scan_schema import (
    ExplainRequest,
    ScanRequest,
    ScanResponse,
    UrlScanRequest,
)
from backend.config import settings
from backend.database.connection import get_db
from backend.services.explanation_service import get_explanation_service
from backend.services.extraction_service import ExtractionError, get_extraction_service
from backend.services.rule_engine import get_rule_engine
from backend.services.scan_service import ScanInput, ScanInputError, get_scan_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["scan"])


@router.post("/scan", response_model=ScanResponse, summary="Analyse a job advertisement")
def create_scan(payload: ScanRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Runs the full detection pipeline and persists the result.

    * Validates the request (Pydantic raises 422 with field-level detail).
    * Combines title/company/description/metadata into one text for the ML model.
    * Runs the ML classifier and the independent rule engine.
    * Blends both into a 0-100 risk score with safety floors.
    * Generates per-rule explanations and safety recommendations.
    * Saves the scan to SQLite and returns it with its id.
    """
    extra = " ".join(part for part in (payload.skills, payload.instructions) if part)

    data = ScanInput(
        job_description=payload.job_description,
        job_title=payload.job_title or "",
        company_name=payload.company_name or "",
        salary=payload.salary or "",
        contact_email=payload.contact_email or "",
        extra=extra,
        source_type=payload.source_type or "text",
        source_url=payload.source_url or "",
        model_name=payload.ollama_model,
        include_ai_explanation=bool(payload.include_ai_explanation),
    )

    try:
        return get_scan_service().execute(db, data)
    except ScanInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/scan/url", response_model=ScanResponse, summary="Fetch a URL and analyse it")
def scan_from_url(payload: UrlScanRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Fetches a public web page, strips navigation/scripts, then runs the same pipeline."""
    try:
        extracted = get_extraction_service().from_url(payload.url)
    except ExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    data = ScanInput(
        job_description=extracted["text"],
        job_title=payload.job_title or extracted.get("page_title", ""),
        company_name=payload.company_name or "",
        source_type="url",
        source_url=extracted["resolved_url"],
        model_name=payload.ollama_model,
        include_ai_explanation=bool(payload.include_ai_explanation),
    )

    try:
        result = get_scan_service().execute(db, data)
    except ScanInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result.setdefault("extracted", {})
    result["extracted"] = {
        "source_type": "url",
        "requested_url": payload.url,
        "resolved_url": extracted["resolved_url"],
        "page_title": extracted["page_title"],
        "characters": extracted["characters"],
    }
    return result


@router.post("/scan/image", response_model=ScanResponse, summary="OCR a screenshot and analyse it")
async def scan_from_image(
    file: UploadFile = File(..., description="Screenshot of the advertisement"),
    job_title: str = Form(""),
    company_name: str = Form(""),
    ollama_model: str = Form(""),
    include_ai_explanation: bool = Form(False),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Extracts text from an uploaded image with Tesseract, then runs the pipeline."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Screenshot exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB limit.",
        )

    try:
        ocr = get_extraction_service().from_image(content)
    except ExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    data = ScanInput(
        job_description=ocr["text"],
        job_title=job_title,
        company_name=company_name,
        source_type="image",
        model_name=ollama_model or None,
        include_ai_explanation=bool(include_ai_explanation),
    )

    try:
        result = get_scan_service().execute(db, data)
    except ScanInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result["extracted"] = {
        "source_type": "image",
        "filename": file.filename,
        "characters": ocr["characters"],
        "image_size": ocr["image_size"],
    }
    return result


@router.post("/scan/explain", summary="Explain an existing verdict with local Ollama")
def explain_scan(payload: ExplainRequest) -> Dict[str, Any]:
    """
    Optional narrative for a verdict that has already been computed.

    The LLM only rewords the result — it cannot alter the score or the risk level.
    """
    return get_explanation_service().explain(
        job_title=payload.job_title or "Job advertisement",
        company=payload.company_name or "Not stated",
        risk_level=payload.risk_level,
        risk_score=payload.risk_score,
        flags=payload.flags,
        model_name=payload.model_name,
    )


@router.get("/rules", summary="List the heuristic rules")
def list_rules() -> Dict[str, Any]:
    """Rule catalogue with weights and severities, for the architecture page."""
    engine = get_rule_engine()
    return {"count": len(engine.rules), "rules": engine.catalogue()}
