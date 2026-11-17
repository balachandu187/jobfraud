"""
JobShield AI — FastAPI Backend Service

Exposes the detection pipeline in `services.py` over HTTP and, when a production
React build is present in `frontend/dist`, serves that single-page app as well.

Endpoints
---------
GET    /api/health              liveness probe (used by start scripts / Docker)
GET    /api/status              engine telemetry (ML ready, Ollama, rule count)
GET    /api/stats               dashboard aggregates + 7-day trend + top warnings
GET    /api/history             audit log, filterable by risk level and free text
GET    /api/history/{scan_id}   single audit record
DELETE /api/history/{scan_id}   delete one record
DELETE /api/history             purge all records
POST   /api/scan                full dual-engine scan (JSON body)
POST   /api/scan/url            fetch a posting from a URL, then scan
POST   /api/scan/image          OCR a screenshot, then scan (multipart upload)
POST   /api/extract             extraction only — returns text + suggested fields
POST   /api/ollama/explain      local LLM narrative for an existing verdict
GET    /api/rules               the heuristic rule catalogue
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from services import DetectionService, InputError, ScanPayload, get_service  # noqa: E402

MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB screenshot cap

app = FastAPI(
    title="JobShield AI — Cyber Threat Intelligence API",
    description="Dual-engine fake job and recruitment scam detection API.",
    version="2.1.0",
)

# The React dev server proxies /api, and the production bundle is same-origin.
# Wide CORS is deliberate so the API stays usable from local tooling.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Schemas
# ---------------------------------------------------------
class ScanRequest(BaseModel):
    job_title: Optional[str] = ""
    company_name: Optional[str] = ""
    salary_info: Optional[str] = ""
    contact_email: Optional[str] = ""
    instructions: Optional[str] = ""
    skills: Optional[str] = ""
    job_description: str = Field(..., min_length=1, description="Full job advertisement text")
    source_url: Optional[str] = None
    source_type: Optional[str] = "text"
    ollama_model: Optional[str] = "llama3.2:latest"
    include_ai_explanation: Optional[bool] = False

    @field_validator("job_description")
    @classmethod
    def _description_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Job description text cannot be empty.")
        if len(value) > 20000:
            raise ValueError("Job description is too long (20,000 character limit).")
        return value


class UrlScanRequest(BaseModel):
    url: str = Field(..., min_length=4, description="Job advertisement URL")
    company_name: Optional[str] = ""
    job_title: Optional[str] = ""
    ollama_model: Optional[str] = "llama3.2:latest"
    include_ai_explanation: Optional[bool] = False


class OllamaExplainRequest(BaseModel):
    job_title: Optional[str] = ""
    company_name: Optional[str] = ""
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: str
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    model_name: Optional[str] = "llama3.2:latest"


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def _service() -> DetectionService:
    try:
        return get_service()
    except Exception as exc:  # pragma: no cover - startup failure path
        raise HTTPException(status_code=503, detail=f"Detection engine unavailable: {exc}") from exc


def _run(payload: ScanPayload) -> Dict[str, Any]:
    try:
        return _service().scan(payload).to_dict()
    except InputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"Scan failed: {exc}") from exc


# ---------------------------------------------------------
# Telemetry
# ---------------------------------------------------------
@app.get("/api/health")
def health() -> Dict[str, Any]:
    """Cheap liveness probe — does not touch Ollama or the database."""
    return {"status": "ok"}


@app.get("/api/status")
def get_system_status() -> Dict[str, Any]:
    """Returns telemetry on ML model readiness and Ollama availability."""
    return _service().status()


@app.get("/api/stats")
def get_dashboard_statistics() -> Dict[str, Any]:
    """Aggregated scan metrics from the SQLite audit trail."""
    return _service().statistics()


@app.get("/api/rules")
def get_rules() -> List[Dict[str, Any]]:
    """Catalogue of heuristic rules, for the architecture page."""
    detector = _service().detector
    return [
        {
            "id": rule["id"],
            "title": rule["title"],
            "category": rule["category"],
            "severity": rule["severity"],
            "weight": rule["weight"],
            "explanation": rule["explanation"],
        }
        for rule in detector.rules
    ]


# ---------------------------------------------------------
# History
# ---------------------------------------------------------
@app.get("/api/history")
def get_scan_history(
    limit: int = Query(100, ge=1, le=500),
    risk_level: Optional[str] = Query(None, description="Low Risk | Medium Risk | High Risk"),
    search: Optional[str] = Query(None, description="Free-text filter"),
) -> List[Dict[str, Any]]:
    allowed = {"Low Risk", "Medium Risk", "High Risk"}
    if risk_level and risk_level not in allowed:
        raise HTTPException(status_code=400, detail=f"risk_level must be one of {sorted(allowed)}")
    return _service().history(limit=limit) if not (risk_level or search) else _service().db.get_recent_scans(
        limit=limit, risk_level=risk_level, search=search
    )


@app.get("/api/history/{scan_id}")
def get_scan_record(scan_id: int) -> Dict[str, Any]:
    record = _service().db.get_scan(scan_id)
    if not record:
        raise HTTPException(status_code=404, detail="Scan record not found")
    return record


@app.delete("/api/history/{scan_id}")
def delete_scan_record(scan_id: int) -> Dict[str, Any]:
    if not _service().delete_scan(scan_id):
        raise HTTPException(status_code=404, detail="Scan record not found")
    return {"success": True, "deleted_id": scan_id}


@app.delete("/api/history")
def clear_all_scan_history() -> Dict[str, Any]:
    _service().clear_history()
    return {"success": True, "message": "All scan records purged"}


# ---------------------------------------------------------
# Scanning
# ---------------------------------------------------------
@app.post("/api/scan")
def scan_job_advertisement(req: ScanRequest) -> Dict[str, Any]:
    """
    Runs the dual-engine pipeline on supplied text:
    ML inference -> 8 heuristic rules -> blended risk + critical floor
    -> safety checklist -> SQLite audit -> optional Ollama narrative.
    """
    payload = ScanPayload(
        job_description=req.job_description,
        job_title=req.job_title or "",
        company_name=req.company_name or "",
        salary_info=req.salary_info or "",
        contact_email=req.contact_email or "",
        instructions=req.instructions or "",
        skills=req.skills or "",
        source_url=req.source_url,
        source_type=req.source_type or "text",
        ollama_model=req.ollama_model or "llama3.2:latest",
        include_ai_explanation=bool(req.include_ai_explanation),
    )
    return _run(payload)


@app.post("/api/scan/url")
def scan_job_from_url(req: UrlScanRequest) -> Dict[str, Any]:
    """Fetches a posting from a URL, extracts readable text, then scans it."""
    service = _service()
    try:
        extracted = service.fetch_from_url(req.url)
    except InputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    payload = ScanPayload(
        job_description=extracted["text"],
        job_title=req.job_title or extracted.get("page_title", ""),
        company_name=req.company_name or "",
        source_url=extracted["url"],
        source_type="url",
        ollama_model=req.ollama_model or "llama3.2:latest",
        include_ai_explanation=bool(req.include_ai_explanation),
    )
    result = _run(payload)
    result["extracted"] = {
        "source_type": "url",
        "requested_url": req.url,
        "resolved_url": extracted["url"],
        "page_title": extracted.get("page_title", ""),
        "characters": len(extracted["text"]),
    }
    return result


@app.post("/api/scan/image")
async def scan_job_from_image(
    file: UploadFile = File(..., description="Screenshot of the job advertisement"),
    job_title: str = Form(""),
    company_name: str = Form(""),
    ollama_model: str = Form("llama3.2:latest"),
    include_ai_explanation: bool = Form(False),
) -> Dict[str, Any]:
    """OCRs an uploaded screenshot, then scans the extracted text."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Screenshot exceeds the 8 MB limit.")

    service = _service()
    try:
        ocr = service.ocr_image(content)
    except InputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    payload = ScanPayload(
        job_description=ocr["text"],
        job_title=job_title or "",
        company_name=company_name or "",
        source_type="image",
        ollama_model=ollama_model or "llama3.2:latest",
        include_ai_explanation=bool(include_ai_explanation),
    )
    result = _run(payload)
    result["extracted"] = {
        "source_type": "image",
        "filename": file.filename,
        "characters": len(ocr["text"]),
        "image_size": f"{ocr['width']}x{ocr['height']}",
    }
    return result


@app.post("/api/extract")
async def extract_text(
    url: Optional[str] = Body(None, embed=True),
    file: Optional[UploadFile] = File(None),
) -> Dict[str, Any]:
    """Extraction only — returns the text without running detection or saving a record."""
    service = _service()
    if url:
        try:
            extracted = service.fetch_from_url(url)
        except InputError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"source_type": "url", **extracted}

    if file is not None:
        content = await file.read()
        try:
            ocr = service.ocr_image(content)
        except InputError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"source_type": "image", "filename": file.filename, **ocr}

    raise HTTPException(status_code=400, detail="Provide either a `url` or a `file`.")


@app.post("/api/ollama/explain")
def generate_ai_explanation(req: OllamaExplainRequest) -> Dict[str, Any]:
    """Generates an on-demand local Ollama summary for an existing analysis."""
    return _service().explain(
        job_title=req.job_title or "Job Advertisement",
        company_name=req.company_name or "Not specified",
        risk_score=req.risk_score,
        risk_level=req.risk_level,
        warnings=req.warnings,
        model_name=req.model_name,
    )


# ---------------------------------------------------------
# Error shaping
# ---------------------------------------------------------
@app.exception_handler(InputError)
async def _input_error_handler(_request, exc: InputError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


# ---------------------------------------------------------
# React production build (optional)
# ---------------------------------------------------------
frontend_dist = os.path.join(CURRENT_DIR, "frontend", "dist")
if os.path.isdir(frontend_dist):
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        candidate = os.path.join(frontend_dist, full_path)
        # Guard against path traversal escaping the dist directory.
        if full_path and os.path.abspath(candidate).startswith(os.path.abspath(frontend_dist)) \
                and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(frontend_dist, "index.html"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api:app",
        host=os.environ.get("JOBSHIELD_HOST", "0.0.0.0"),
        port=int(os.environ.get("JOBSHIELD_PORT", "8000")),
        reload=os.environ.get("JOBSHIELD_RELOAD", "0") == "1",
    )
