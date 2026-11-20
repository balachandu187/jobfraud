"""
JobShield AI — FastAPI Backend Service
Wraps existing ML, Heuristic, Risk Analysis, and SQLite modules
without altering or mocking any underlying detection algorithms.
Serves the modern React SaaS interface and REST API endpoints.
"""

import os
import sys
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# Ensure JobShieldAI directory is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
load_dotenv(os.path.join(current_dir, ".env"))

# Import existing core modules
from model.predictor import JobPredictor
from utils.detector import ScamDetector
from utils.risk_analyzer import RiskAnalyzer
from utils.explanation import get_safety_recommendations
from utils.ollama_client import OllamaClient
from database.db_manager import DatabaseManager
from utils.auth import hash_password, verify_password, create_auth_token, verify_auth_token

app = FastAPI(
    title="JobShield AI — Cyber Threat Intelligence API",
    description="Dual-Engine Fake Job and Recruitment Scam Detection API with Enterprise Security",
    version="2.1.0"
)

# Enable CORS for local development & frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize singletons
db = DatabaseManager()
predictor = JobPredictor(model_dir=os.path.join(current_dir, "saved_models"))
detector = ScamDetector()
analyzer = RiskAnalyzer()
ollama = OllamaClient()

# Security Dependency
def get_current_user_optional(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    """Extracts authenticated user from Bearer header if provided."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split("Bearer ", 1)[1].strip()
    return verify_auth_token(token)

def require_auth(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Guards endpoints ensuring a valid cryptographic bearer token is presented."""
    user = get_current_user_optional(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required or session expired.")
    return user


# ---------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)

class LoginRequest(BaseModel):
    email: str
    password: str

class GoogleAuthRequest(BaseModel):
    id_token: str = Field(..., min_length=1)

class ScanRequest(BaseModel):
    job_title: Optional[str] = ""
    company_name: Optional[str] = ""
    salary_info: Optional[str] = ""
    contact_email: Optional[str] = ""
    instructions: Optional[str] = ""
    skills: Optional[str] = ""
    job_description: str = Field(..., min_length=1, description="Full job advertisement text")
    ollama_model: Optional[str] = "llama3.2:latest"
    include_ai_explanation: Optional[bool] = False

class OllamaExplainRequest(BaseModel):
    job_title: Optional[str] = ""
    company_name: Optional[str] = ""
    risk_score: int
    risk_level: str
    warnings: List[Dict[str, Any]] = []
    model_name: Optional[str] = "llama3.2:latest"


# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------

@app.post("/api/auth/register")
def register_user(req: RegisterRequest) -> Dict[str, Any]:
    """Registers a new security analyst with salted PBKDF2 credentials."""
    existing = db.get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email address already exists.")
    
    pw_hash, salt = hash_password(req.password)
    user_id = db.create_user(req.email, pw_hash, salt, req.full_name)
    if not user_id:
        raise HTTPException(status_code=500, detail="Failed to create user account.")
    
    token = create_auth_token(user_id, req.email.lower().strip(), "analyst", req.full_name.strip())
    return {
        "success": True,
        "token": token,
        "user": {
            "id": user_id,
            "email": req.email.lower().strip(),
            "name": req.full_name.strip(),
            "role": "analyst"
        }
    }

@app.post("/api/auth/login")
def login_user(req: LoginRequest) -> Dict[str, Any]:
    """Authenticates credentials and issues cryptographic bearer token."""
    user = db.get_user_by_email(req.email)
    if not user or not verify_password(req.password, user["password_hash"], user["salt"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    
    token = create_auth_token(user["id"], user["email"], user["role"], user["full_name"])
    return {
        "success": True,
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["full_name"],
            "role": user["role"]
        }
    }

@app.get("/api/auth/google/config")
def google_auth_config() -> Dict[str, Any]:
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    return {
        "configured": bool(client_id),
        "client_id": client_id,
        "setup_message": "Create a Google OAuth 2.0 Web client and set GOOGLE_CLIENT_ID in JobShieldAI/.env.",
    }


@app.post("/api/auth/google")
def google_authenticate(req: GoogleAuthRequest) -> Dict[str, Any]:
    """Verifies a Google ID token and creates or logs in the Google user."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured.")

    try:
        claims = id_token.verify_oauth2_token(
            req.id_token,
            google_requests.Request(),
            client_id,
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired Google ID token.")

    if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise HTTPException(status_code=401, detail="Invalid Google token issuer.")
    if claims.get("email_verified") is not True:
        raise HTTPException(status_code=401, detail="Google email is not verified.")

    email = str(claims.get("email", "")).strip().lower()
    name = str(claims.get("name", "")).strip() or email.split("@")[0]
    avatar_url = str(claims.get("picture", "")).strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Google identity did not include a valid email.")

    user = db.upsert_google_user(email, name, avatar_url)
    token = create_auth_token(user["id"], user["email"], user["role"], user["full_name"])
    return {
        "success": True,
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["full_name"],
            "role": user["role"],
            "auth_provider": "google",
            "avatar_url": user.get("avatar_url", "")
        }
    }

@app.get("/api/auth/me")
def get_current_user_profile(user: Dict[str, Any] = Depends(require_auth)) -> Dict[str, Any]:
    """Validates session and returns current authenticated identity."""
    return {"authenticated": True, "user": user}

@app.get("/api/status")
def get_system_status() -> Dict[str, Any]:
    """Returns telemetry on ML model readiness and Ollama engine availability."""
    ollama_online = ollama.is_available()
    models = ollama.list_models() if ollama_online else []
    return {
        "status": "online",
        "service": "JobShield AI Core",
        "ml_ready": predictor.is_ready,
        "ollama_available": ollama_online,
        "ollama_models": models if models else ["llama3.2:latest", "gemma:2b", "mistral"],
        "active_ollama_model": ollama.model_name
    }


@app.get("/api/stats")
def get_dashboard_statistics() -> Dict[str, Any]:
    """Retrieves aggregated scan metrics from the SQLite database."""
    stats = db.get_statistics()
    return {
        "total_scans": stats["total_scans"],
        "low_risk_count": stats["low_risk_count"],
        "medium_risk_count": stats["medium_risk_count"],
        "high_risk_count": stats["high_risk_count"],
        "average_risk_score": stats["average_risk_score"]
    }


@app.get("/api/history")
def get_scan_history(limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieves chronological audit logs of scanned advertisements."""
    return db.get_recent_scans(limit=limit)


@app.delete("/api/history/{scan_id}")
def delete_scan_record(scan_id: int) -> Dict[str, Any]:
    """Deletes a single scan log by ID."""
    success = db.delete_scan(scan_id)
    if not success:
        raise HTTPException(status_code=404, detail="Scan record not found")
    return {"success": True, "deleted_id": scan_id}


@app.delete("/api/history")
def clear_all_scan_history() -> Dict[str, Any]:
    """Purges all historical scan entries."""
    db.clear_all_history()
    return {"success": True, "message": "All scan records purged"}


@app.post("/api/scan")
def scan_job_advertisement(req: ScanRequest) -> Dict[str, Any]:
    """
    Executes the Dual-Engine Hybrid Pipeline:
    1. Aggregates metadata + text for NLP
    2. Runs Scikit-learn TF-IDF + Logistic Regression
    3. Runs Rule-Based Heuristic Scanner (8 Regex Patterns)
    4. Blends Composite Risk Score & enforces Critical safety floor
    5. Generates tailored safety checklists
    6. Persists audit record in SQLite
    7. Optionally generates local Ollama LLM synthesis
    """
    # 1. Aggregation
    aggregated_text = (
        f"{req.job_title} {req.company_name} {req.salary_info} {req.contact_email} "
        f"{req.instructions} {req.skills} {req.job_description}"
    ).strip()

    if not req.job_description.strip():
        raise HTTPException(status_code=400, detail="Job description text cannot be empty.")

    # 2. ML Inference
    ml_result = predictor.predict(aggregated_text)

    # 3. Rule Heuristics
    heuristic_text = f"{req.salary_info} {req.contact_email} {req.instructions} {req.job_description}"
    rule_result = detector.analyze(
        text=heuristic_text,
        company=req.company_name or ""
    )

    # 4. Ensemble Risk Blending
    risk_result = analyzer.calculate_risk(ml_result, rule_result)

    # 5. Safety Recommendations
    safety_tips = get_safety_recommendations(
        risk_result["risk_level"],
        risk_result["warnings"]
    )

    # 6. Database Persistence
    scan_id = db.save_scan(
        job_text=req.job_description,
        prediction=risk_result["verdict"],
        risk_score=risk_result["risk_score"],
        risk_level=risk_result["risk_level"],
        job_title=req.job_title or "Unspecified Title",
        company_name=req.company_name or "Unspecified Employer",
        warnings=risk_result["warnings"]
    )

    # 7. Local AI Synthesis (optional on scan)
    ai_explanation = None
    if req.include_ai_explanation:
        if req.ollama_model:
            ollama.model_name = req.ollama_model
        ai_explanation = ollama.generate_explanation(
            job_title=req.job_title or "Job Advertisement",
            company=req.company_name or "Not specified",
            risk_score=risk_result["risk_score"],
            risk_level=risk_result["risk_level"],
            warnings=risk_result["warnings"]
        )

    return {
        "scan_id": scan_id,
        "job_title": req.job_title or "Unspecified Title",
        "company_name": req.company_name or "Unspecified Employer",
        "salary_info": req.salary_info or "",
        "contact_email": req.contact_email or "",
        "job_description": req.job_description,
        "ml_result": ml_result,
        "rule_result": rule_result,
        "risk_result": risk_result,
        "safety_tips": safety_tips,
        "ai_explanation": ai_explanation
    }


@app.post("/api/ollama/explain")
def generate_ai_explanation(req: OllamaExplainRequest) -> Dict[str, Any]:
    """Generates on-demand local Ollama summary for an existing analysis."""
    if req.model_name:
        ollama.model_name = req.model_name
    result = ollama.generate_explanation(
        job_title=req.job_title or "Job Advertisement",
        company=req.company_name or "Not specified",
        risk_score=req.risk_score,
        risk_level=req.risk_level,
        warnings=req.warnings
    )
    return result


# ---------------------------------------------------------
# Static Frontend Files Mount (React Production Build)
# ---------------------------------------------------------
frontend_dist = os.path.join(current_dir, "frontend", "dist")
if os.path.exists(frontend_dist):
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Don't intercept API routes
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        file_path = os.path.join(frontend_dist, full_path)
        if full_path and os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
