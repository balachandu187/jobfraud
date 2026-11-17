"""Pydantic schemas for scan requests and responses."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from backend.config import settings


class ScanRequest(BaseModel):
    """
    Body of POST /api/scan.

    `job_description` is the only required field. Extra metadata is optional but
    improves accuracy because the ML model was trained on title/company/description
    together.
    """

    job_title: Optional[str] = Field("", max_length=300, description="Job title, e.g. Software Developer")
    company_name: Optional[str] = Field("", max_length=300, description="Employer name")
    job_description: str = Field(..., min_length=1, description="Full advertisement text")
    salary: Optional[str] = Field("", max_length=200, description="Offered salary, e.g. 50000 per month")
    contact_email: Optional[str] = Field("", max_length=320, description="Recruiter email address")

    # Optional extras used by the richer UI
    skills: Optional[str] = Field("", max_length=2000)
    instructions: Optional[str] = Field("", max_length=4000)
    source_url: Optional[str] = None
    source_type: str = Field("text", pattern="^(text|url|image)$")
    ollama_model: Optional[str] = None
    include_ai_explanation: bool = False

    @field_validator("job_description")
    @classmethod
    def _validate_description(cls, value: str) -> str:
        text = (value or "").strip()
        if not text:
            raise ValueError("job_description cannot be empty or whitespace only")
        if len(text) > settings.max_description_chars:
            raise ValueError(
                f"job_description exceeds the {settings.max_description_chars}-character limit"
            )
        return value

    @field_validator("contact_email")
    @classmethod
    def _validate_email(cls, value: Optional[str]) -> Optional[str]:
        """Lenient: recruiters sometimes put 'hr at company dot com' or a URL here."""
        if not value:
            return ""
        candidate = value.strip()
        if len(candidate) > 320:
            raise ValueError("contact_email is too long")
        return candidate

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_title": "Software Developer",
                "company_name": "ABC Technologies",
                "job_description": (
                    "Apply for the Software Developer role. Pay a refundable registration "
                    "fee of 2000 to confirm your seat. No interview required."
                ),
                "salary": "50000 per month",
                "contact_email": "hr.recruiter@gmail.com",
            }
        }
    )


class FlagSchema(BaseModel):
    """One triggered heuristic."""

    id: str
    flag: str
    severity: str
    weight: int
    category: str
    explanation: str
    evidence: str = ""


class ScoreBreakdown(BaseModel):
    """Transparency record of how the final score was produced."""

    model_config = ConfigDict(extra="allow")

    ml_score: float
    rule_score: int
    ml_weight: float
    rule_weight: float
    blended_score: float
    enforced_floor: int
    floor_reasons: List[str]
    final_score: int
    formula: str


class ScanResponse(BaseModel):
    """
    Response of POST /api/scan.

    Carries both the spec-level summary (`prediction`, `rule_based_flags`,
    `recommendations`) and the richer nested data the existing React UI renders.
    """

    model_config = ConfigDict(extra="allow")

    success: bool = True
    scan_id: Optional[int] = None
    prediction: str
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: str
    ml_prediction: str
    ml_probability: float = Field(..., ge=0.0, le=1.0)
    rule_based_flags: List[FlagSchema] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    explanation: str
    score_breakdown: ScoreBreakdown

    job_title: str = ""
    company_name: str = ""
    salary: str = ""
    contact_email: str = ""
    source_type: str = "text"
    source_url: str = ""

    ai_explanation: Optional[Dict[str, Any]] = None
    storage_warning: Optional[str] = None


class UrlScanRequest(BaseModel):
    """Body of POST /api/scan/url."""

    url: str = Field(..., min_length=4, description="Public http(s) URL of the posting")
    job_title: Optional[str] = ""
    company_name: Optional[str] = ""
    ollama_model: Optional[str] = None
    include_ai_explanation: bool = False


class ExplainRequest(BaseModel):
    """Body of POST /api/scan/explain."""

    job_title: Optional[str] = ""
    company_name: Optional[str] = ""
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: str
    flags: List[Dict[str, Any]] = Field(default_factory=list)
    model_name: Optional[str] = None
