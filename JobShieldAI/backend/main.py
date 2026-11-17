"""
JobShield AI — FastAPI application entry point.

Run with:
    uvicorn backend.main:app --reload
or:
    python -m backend.main

Serves the REST API and, when a production React build exists in `frontend/dist`,
serves that single-page app from the same origin (so no dev proxy is needed in
production and the CORS list stays short).

Swagger UI: http://127.0.0.1:8000/docs
ReDoc:      http://127.0.0.1:8000/redoc
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.api.routes import dashboard, health, history, scan
from backend.config import settings
from backend.database.connection import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("jobshield")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Creates tables, migrates legacy rows and loads the ML model once at startup."""
    logger.info("Starting %s v%s (%s)", settings.app_name, settings.app_version, settings.environment)
    init_db()

    # Importing the scan service here loads the model a single time for the whole process.
    from backend.services.scan_service import get_scan_service

    service = get_scan_service()
    if service.ml.is_ready:
        logger.info("ML model loaded from %s", service.ml.model_dir)
    else:
        logger.warning("ML model NOT loaded: %s", service.ml.load_error)
    logger.info("Rule engine ready with %d rules", len(service.rules.rules))

    yield

    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=f"{settings.app_name} API",
    description=(
        "Fake job and recruitment-scam detection.\n\n"
        "**Dual-engine design**: a TF-IDF + Logistic Regression classifier and an "
        "independent rule engine, blended into a 0-100 risk score with documented safety "
        "floors. Scores are estimates, not proof of fraud."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS: explicit origins read from config, not a wildcard. The React dev server runs on
# :5173; the list is overridable with JOBSHIELD_CORS_ORIGINS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
    max_age=600,
)


# ---------------------------------------------------------------------------
# Error handling — always return JSON, never a stack trace
# ---------------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def _http_error(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def _unhandled_error(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check the server log for details."},
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health.router)
app.include_router(scan.router)
app.include_router(history.router)
app.include_router(dashboard.router)


@app.get("/api/ollama/explain", include_in_schema=False)
@app.post("/api/ollama/explain", include_in_schema=False, tags=["scan"])
def legacy_ollama_explain(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Backwards-compatible path used by the current React build.

    Delegates to the explanation service; `warnings` and `flags` are both accepted.
    """
    from backend.services.explanation_service import get_explanation_service

    return get_explanation_service().explain(
        job_title=payload.get("job_title") or "Job advertisement",
        company=payload.get("company_name") or "Not stated",
        risk_level=payload.get("risk_level") or "Unknown",
        risk_score=int(payload.get("risk_score") or 0),
        flags=payload.get("flags") or payload.get("warnings") or [],
        model_name=payload.get("model_name"),
    )


# ---------------------------------------------------------------------------
# React single-page app (optional)
# ---------------------------------------------------------------------------
frontend_dist = settings.frontend_dist
if (frontend_dist / "index.html").is_file():
    assets = frontend_dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:
        """Serves built files, falling back to index.html for client-side routes."""
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        candidate = (frontend_dist / full_path).resolve()
        dist_root = frontend_dist.resolve()
        # Path traversal guard: the resolved path must stay inside dist/.
        if full_path and dist_root in candidate.parents and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/", include_in_schema=False)
    async def build_missing() -> HTMLResponse:
        """Explains how to build the UI instead of returning a bare 404."""
        return HTMLResponse(
            """
            <!doctype html><html><head><meta charset="utf-8">
            <title>JobShield AI — UI not built</title>
            <style>
              body{background:#0B0F19;color:#F8FAFC;font-family:system-ui,sans-serif;
                   display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
              .card{max-width:560px;padding:40px;border:1px solid #1E293B;border-radius:16px;background:#111827}
              h1{font-size:20px;margin:0 0 12px}
              code{background:#1E293B;padding:2px 6px;border-radius:4px;color:#93C5FD}
              p{color:#94A3B8;line-height:1.6;font-size:14px}
              a{color:#60A5FA}
            </style></head><body><div class="card">
              <h1>&#128737; JobShield AI API is running</h1>
              <p>The React interface has not been built yet. Build it once:</p>
              <p><code>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</code></p>
              <p>The API is live now: <a href="/docs">/docs</a> &middot;
                 <a href="/api/health">/api/health</a> &middot;
                 <a href="/api/dashboard">/api/dashboard</a></p>
            </div></body></html>
            """
        )


def run() -> None:
    """Console entry point: `python -m backend.main`."""
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )


if __name__ == "__main__":
    run()
