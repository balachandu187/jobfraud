"""
Central configuration for the JobShield AI backend.

Every value can be overridden with an environment variable, so nothing needs editing
to move between a laptop demo and a server deployment. Defaults are chosen so the app
runs with zero configuration on a fresh checkout.

Import the settings object, not `os.environ`:

    from backend.config import settings
    settings.database_url
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parent          # .../JobShieldAI/backend
PROJECT_ROOT = BASE_DIR.parent                      # .../JobShieldAI


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    # ---- Application -------------------------------------------------
    app_name: str = "JobShield AI"
    app_version: str = "3.0.0"
    environment: str = os.environ.get("JOBSHIELD_ENV", "development")
    host: str = os.environ.get("JOBSHIELD_HOST", "0.0.0.0")
    port: int = _env_int("JOBSHIELD_PORT", 8000)
    reload: bool = _env_bool("JOBSHIELD_RELOAD", False)

    # ---- Database ----------------------------------------------------
    #: SQLite file. Deliberately distinct from the pre-SQLAlchemy `jobshield.db` so the
    #: previous schema is never mutated; legacy rows are imported once (see database/connection.py).
    database_filename: str = os.environ.get("JOBSHIELD_DB_FILE", "jobshield_v3.db")
    legacy_database_filename: str = "jobshield.db"
    sql_echo: bool = _env_bool("JOBSHIELD_SQL_ECHO", False)

    # ---- Machine learning --------------------------------------------
    model_dir: Path = Path(os.environ.get("JOBSHIELD_MODEL_DIR", PROJECT_ROOT / "saved_models"))
    dataset_path: Path = Path(os.environ.get("JOBSHIELD_DATASET", PROJECT_ROOT / "data" / "jobs.csv"))
    #: Weights for the ensemble. Must sum to 1.0; validated at startup.
    ml_weight: float = _env_float("JOBSHIELD_ML_WEIGHT", 0.50)
    rule_weight: float = _env_float("JOBSHIELD_RULE_WEIGHT", 0.50)
    #: Safety floors (see services/risk_analyzer.py).
    critical_floor: int = _env_int("JOBSHIELD_CRITICAL_FLOOR", 75)
    elevated_floor: int = _env_int("JOBSHIELD_ELEVATED_FLOOR", 45)
    #: Risk tier boundaries.
    low_risk_max: int = _env_int("JOBSHIELD_LOW_MAX", 34)
    high_risk_min: int = _env_int("JOBSHIELD_HIGH_MIN", 66)

    # ---- Input limits ------------------------------------------------
    max_description_chars: int = _env_int("JOBSHIELD_MAX_TEXT", 20000)
    max_upload_bytes: int = _env_int("JOBSHIELD_MAX_UPLOAD", 8 * 1024 * 1024)

    # ---- Ollama (optional, explanatory only) -------------------------
    ollama_url: str = os.environ.get("JOBSHIELD_OLLAMA_URL", "http://localhost:11434")
    ollama_model: str = os.environ.get("JOBSHIELD_OLLAMA_MODEL", "llama3.2:latest")
    ollama_timeout: float = _env_float("JOBSHIELD_OLLAMA_TIMEOUT", 60.0)
    ollama_health_timeout: float = _env_float("JOBSHIELD_OLLAMA_HEALTH_TIMEOUT", 1.5)

    # ---- URL ingestion -----------------------------------------------
    url_fetch_timeout: float = _env_float("JOBSHIELD_URL_TIMEOUT", 10.0)
    url_max_bytes: int = _env_int("JOBSHIELD_URL_MAX_BYTES", 2_000_000)
    url_max_redirects: int = _env_int("JOBSHIELD_URL_MAX_REDIRECTS", 4)
    ca_bundle: str = os.environ.get("JOBSHIELD_CA_BUNDLE", "/etc/ssl/certs/ca-certificates.crt")

    # ---- CORS --------------------------------------------------------
    #: The React dev server runs on 5173 (Vite). Anything else must be added explicitly;
    #: wildcard origins are intentionally NOT the default.
    cors_origins: List[str] = field(default_factory=lambda: _parse_origins(
        os.environ.get(
            "JOBSHIELD_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,"
            "http://localhost:8000,http://127.0.0.1:8000,"
            "http://localhost:3000,http://127.0.0.1:3000",
        )
    ))

    @property
    def database_url(self) -> str:
        path = PROJECT_ROOT / "database" / self.database_filename
        return f"sqlite:///{path}"

    @property
    def database_path(self) -> Path:
        return PROJECT_ROOT / "database" / self.database_filename

    @property
    def legacy_database_path(self) -> Path:
        return PROJECT_ROOT / "database" / self.legacy_database_filename

    @property
    def frontend_dist(self) -> Path:
        return PROJECT_ROOT / "frontend" / "dist"

    def validate(self) -> List[str]:
        """Returns a list of configuration problems; empty means valid."""
        problems: List[str] = []
        if abs((self.ml_weight + self.rule_weight) - 1.0) > 1e-6:
            problems.append(
                f"ml_weight ({self.ml_weight}) + rule_weight ({self.rule_weight}) must equal 1.0"
            )
        if not 0 <= self.critical_floor <= 100:
            problems.append("critical_floor must be within 0-100")
        if not 0 <= self.low_risk_max < self.high_risk_min <= 100:
            problems.append("require low_risk_max < high_risk_min, both within 0-100")
        return problems


def _parse_origins(raw: str) -> List[str]:
    """Parses a comma-separated origin list, dropping empties and trailing slashes."""
    origins = []
    for part in (raw or "").split(","):
        origin = part.strip().rstrip("/")
        if origin:
            origins.append(origin)
    return origins


settings = Settings()

_problems = settings.validate()
if _problems:  # fail fast: a misconfigured weight silently distorts every score
    raise RuntimeError("Invalid JobShield configuration: " + "; ".join(_problems))
