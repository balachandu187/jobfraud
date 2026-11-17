"""
Tests for POST /api/scan and the detection pipeline behind it.

Covers: input validation, ML inference contract, every heuristic rule, the risk blend
and safety floors, recommendation generation, HTTP response shape, Ollama isolation and
storage-failure resilience.
"""

from __future__ import annotations

import pytest

from backend.services.ml_service import MLService
from backend.services.risk_analyzer import HIGH_RISK, LOW_RISK, MEDIUM_RISK, RiskAnalyzer
from backend.services.rule_engine import get_rule_engine
from backend.services.scan_service import ScanInput, ScanService, ScanInputError

SCAM = (
    "Work from home data entry job. Earn ₹80,000 per month doing simple typing. "
    "Pay a refundable registration fee of ₹2,000 to confirm your seat. "
    "No interview required. Contact HR on Telegram @FastCareersAdmin."
)
GENUINE = (
    "Senior Software Engineer at ABC Technologies Ltd. You will design and maintain "
    "distributed backend services in Python and PostgreSQL. Candidates complete two "
    "technical interviews and a coding assessment. Apply via our official careers portal."
)
#: A legitimate posting that mentions the same sensitive words as a scam.
HARD_NEGATIVE = (
    "Payroll & Compliance Officer. During statutory onboarding you will collect and verify "
    "new-joiner bank account details and PAN/Aadhaar documentation under our ISO 27001 "
    "policy. B.Com with three years payroll compliance experience. Background verification "
    "is completed after a written offer is signed."
)


# ---------------------------------------------------------------------------
# Rule engine
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "text,rule_id",
    [
        ("Pay a registration fee of 2000 to apply.", "REGISTRATION_FEE"),
        ("An advance payment for the training kit is required.", "ADVANCE_PAYMENT"),
        ("Submit a refundable security deposit of 5000.", "SECURITY_DEPOSIT"),
        ("Guaranteed selection for all applicants.", "GUARANTEED_SELECTION"),
        ("No interview required, direct joining.", "NO_INTERVIEW"),
        ("Earn Rs 90,000 per month for simple typing work.", "UNREALISTIC_SALARY"),
        ("Urgent hiring! Limited seats available.", "URGENT_PRESSURE"),
        ("Email your CV to hr.jobs@gmail.com", "PERSONAL_EMAIL"),
        ("Contact HR on WhatsApp only.", "SUSPICIOUS_CHANNEL"),
        ("Share the OTP you receive to confirm joining.", "OTP_REQUEST"),
        ("Send your bank passbook photo and net banking password.", "BANK_DETAILS_REQUEST"),
        ("Send your Aadhaar card copy and PAN card details.", "IDENTITY_DOCUMENTS_REQUEST"),
    ],
)
def test_each_rule_fires(text, rule_id):
    result = get_rule_engine().analyze(text, company="Some Company Ltd")
    assert rule_id in [flag["id"] for flag in result["flags"]], result["flags"]


def test_absence_rules_fire_only_when_data_is_missing():
    engine = get_rule_engine()
    missing = engine.analyze("Short ad.", company="")
    ids = [flag["id"] for flag in missing["flags"]]
    assert "MISSING_COMPANY" in ids
    assert "VAGUE_DESCRIPTION" in ids


def test_absence_rules_stay_silent_when_data_is_present():
    result = get_rule_engine().analyze(GENUINE, company="ABC Technologies Ltd")
    ids = [flag["id"] for flag in result["flags"]]
    assert "MISSING_COMPANY" not in ids
    assert "VAGUE_DESCRIPTION" not in ids


def test_weak_signals_alone_cannot_reach_high_risk():
    """Missing company + vague text are weak: they must not produce a High Risk verdict."""
    rule_result = get_rule_engine().analyze("Apply now.", company="")
    risk = RiskAnalyzer().analyze(
        {"fraud_probability": 0.0, "prediction_label": "Genuine", "is_ready": True},
        rule_result,
    )
    assert risk["risk_level"] == LOW_RISK, risk["score_breakdown"]


def test_low_risk_gives_verification_checks():
    result = get_rule_engine().analyze(GENUINE, company="ABC Technologies Ltd")
    assert result["flags"] == []
    assert result["rule_score"] == 0


def test_rule_score_is_capped_at_100():
    result = get_rule_engine().analyze(SCAM * 5, company="X")
    assert 0 <= result["rule_score"] <= 100


def test_every_rule_has_an_advisory():
    from backend.services.explanation_service import ADVISORIES

    missing = [rule.id for rule in get_rule_engine().rules if rule.id not in ADVISORIES]
    assert missing == [], f"rules without recommendations: {missing}"


def test_flags_carry_evidence():
    result = get_rule_engine().analyze(SCAM, company="FastCareers")
    flagged = {flag["id"]: flag for flag in result["flags"]}
    assert flagged["REGISTRATION_FEE"]["evidence"]
    assert "fee" in flagged["REGISTRATION_FEE"]["evidence"].lower()


# ---------------------------------------------------------------------------
# Risk analyzer
# ---------------------------------------------------------------------------
def test_critical_flag_enforces_floor():
    risk = RiskAnalyzer().analyze(
        {"fraud_probability": 0.01, "prediction_label": "Genuine", "is_ready": True},
        {"rule_score": 5, "flags": [{"id": "OTP_REQUEST", "severity": "CRITICAL"}]},
    )
    assert risk["risk_score"] >= 75
    assert risk["risk_level"] == HIGH_RISK
    assert risk["score_breakdown"]["enforced_floor"] == 75


def test_high_flag_prevents_low_risk():
    risk = RiskAnalyzer().analyze(
        {"fraud_probability": 0.0, "prediction_label": "Genuine", "is_ready": True},
        {"rule_score": 0, "flags": [{"id": "NO_INTERVIEW", "severity": "HIGH"}]},
    )
    assert risk["risk_level"] in (MEDIUM_RISK, HIGH_RISK)
    assert risk["risk_score"] >= 45


def test_two_medium_flags_prevent_low_risk():
    risk = RiskAnalyzer().analyze(
        {"fraud_probability": 0.0, "prediction_label": "Genuine", "is_ready": True},
        {"rule_score": 0, "flags": [
            {"id": "PERSONAL_EMAIL", "severity": "MEDIUM"},
            {"id": "URGENT_PRESSURE", "severity": "MEDIUM"},
        ]},
    )
    assert risk["risk_score"] >= 45


def test_clean_input_scores_low():
    risk = RiskAnalyzer().analyze(
        {"fraud_probability": 0.05, "prediction_label": "Genuine", "is_ready": True},
        {"rule_score": 0, "flags": []},
    )
    assert risk["risk_level"] == LOW_RISK
    assert risk["risk_score"] <= 10


def test_score_breakdown_documents_the_formula():
    risk = RiskAnalyzer().analyze(
        {"fraud_probability": 0.6, "prediction_label": "Fraudulent", "is_ready": True},
        {"rule_score": 40, "flags": []},
    )
    breakdown = risk["score_breakdown"]
    expected = (60.0 * breakdown["ml_weight"]) + (40 * breakdown["rule_weight"])
    assert breakdown["blended_score"] == pytest.approx(round(expected, 1))
    assert "x" in breakdown["formula"]


def test_score_is_clamped():
    risk = RiskAnalyzer().analyze(
        {"fraud_probability": 1.0, "prediction_label": "Fraudulent", "is_ready": True},
        {"rule_score": 100, "flags": []},
    )
    assert risk["risk_score"] == 100


def test_weights_are_normalised():
    analyzer = RiskAnalyzer(ml_weight=2, rule_weight=1)
    assert pytest.approx(analyzer.ml_weight + analyzer.rule_weight) == 1.0


def test_verdict_wording_is_hedged():
    """The output must never claim a job is definitely fraudulent."""
    risk = RiskAnalyzer().analyze(
        {"fraud_probability": 0.99, "prediction_label": "Fraudulent", "is_ready": True},
        {"rule_score": 100, "flags": []},
    )
    assert "Possibly" in risk["prediction"]
    assert "not proof" in risk["disclaimer"].lower()


# ---------------------------------------------------------------------------
# ML service
# ---------------------------------------------------------------------------
def test_model_is_loaded():
    service = MLService()
    assert service.is_ready, service.load_error


def test_model_separates_scam_from_genuine():
    service = MLService()
    scam = service.predict(SCAM)["fraud_probability"]
    genuine = service.predict(GENUINE)["fraud_probability"]
    assert scam > 0.7
    assert genuine < 0.5
    assert scam - genuine > 0.3


def test_model_handles_empty_and_odd_input():
    service = MLService()
    assert service.predict("")["fraud_probability"] == 0.0
    assert service.predict("🙂🙂")["is_ready"] is True
    assert service.predict("x" * 40000)["is_ready"] is True


def test_missing_model_reports_unavailable_instead_of_faking(tmp_path):
    """Regression guard: never invent a prediction when artifacts are absent."""
    service = MLService(model_dir=tmp_path)
    assert service.is_ready is False
    result = service.predict("anything at all")
    assert result["is_ready"] is False
    assert result["prediction_label"] == "Model Unavailable"
    assert result["fraud_probability"] == 0.5


def test_unavailable_model_is_disclosed_in_the_response():
    from backend.services.scan_service import ScanService

    service = ScanService(ml_service=MLService(model_dir="/nonexistent-path"))
    analysis = service.analyse(ScanInput(job_description=SCAM, company_name="X"))
    assert "rule engine alone" in analysis["risk_result"]["explanation"]


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------
def test_recommendations_match_the_flags():
    analysis = ScanService().analyse(ScanInput(job_description=SCAM, company_name="FastCareers"))
    recs = " ".join(analysis["recommendations"]).lower()
    assert "registration" in recs
    assert "interview" in recs
    assert "cybercrime" in recs


def test_genuine_job_gets_verification_advice():
    analysis = ScanService().analyse(
        ScanInput(job_description=GENUINE, company_name="ABC Technologies Ltd")
    )
    assert len(analysis["recommendations"]) == 3
    assert any("careers" in rec.lower() for rec in analysis["recommendations"])


# ---------------------------------------------------------------------------
# Service pipeline
# ---------------------------------------------------------------------------
def test_pipeline_flags_scam():
    analysis = ScanService().analyse(ScanInput(job_description=SCAM, company_name="FastCareers"))
    assert analysis["risk_result"]["risk_level"] == HIGH_RISK
    ids = [flag["id"] for flag in analysis["risk_result"]["flags"]]
    assert "REGISTRATION_FEE" in ids and "NO_INTERVIEW" in ids


def test_pipeline_passes_genuine_job():
    analysis = ScanService().analyse(
        ScanInput(job_description=GENUINE, company_name="ABC Technologies Ltd")
    )
    assert analysis["risk_result"]["risk_level"] == LOW_RISK


def test_pipeline_does_not_false_positive_on_legitimate_kyc_role():
    """The hard case: legitimate mention of bank/Aadhaar details must not be fraud."""
    analysis = ScanService().analyse(
        ScanInput(job_description=HARD_NEGATIVE, company_name="Arthik Solutions")
    )
    assert analysis["risk_result"]["risk_level"] == LOW_RISK, analysis["risk_result"]["flags"]


def test_blank_description_is_rejected():
    with pytest.raises(ScanInputError):
        ScanService().analyse(ScanInput(job_description="   "))


def test_overlong_description_is_rejected():
    with pytest.raises(ScanInputError):
        ScanService().analyse(ScanInput(job_description="x" * 25000))


# ---------------------------------------------------------------------------
# HTTP API
# ---------------------------------------------------------------------------
def test_scan_endpoint_returns_spec_shape(client):
    response = client.post("/api/scan", json={
        "job_title": "Software Developer",
        "company_name": "ABC Technologies",
        "job_description": SCAM,
        "salary": "50000 per month",
        "contact_email": "hr.recruiter@gmail.com",
    })
    assert response.status_code == 200, response.text
    body = response.json()

    # Fields required by the project spec
    assert body["success"] is True
    assert isinstance(body["scan_id"], int)
    assert body["risk_level"] == "High Risk"
    assert 0 <= body["risk_score"] <= 100
    assert body["ml_prediction"] in ("Genuine", "Fraudulent")
    assert body["rule_based_flags"]
    assert body["recommendations"]
    flag = body["rule_based_flags"][0]
    assert {"id", "flag", "severity", "explanation", "evidence"} <= set(flag)

    # Fields required by the existing React UI
    assert body["risk_result"]["risk_level"] == "High Risk"
    assert body["ml_result"]["fraud_score_pct"] > 0
    assert body["safety_tips"] == body["recommendations"]
    assert "score_breakdown" in body


def test_scan_persists_to_database(client):
    response = client.post("/api/scan", json={"job_description": SCAM, "company_name": "FastCareers"})
    scan_id = response.json()["scan_id"]
    fetched = client.get(f"/api/history/{scan_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == scan_id


def test_scan_rejects_empty_description(client):
    assert client.post("/api/scan", json={"job_description": "   "}).status_code == 422


def test_scan_rejects_missing_body_field(client):
    assert client.post("/api/scan", json={}).status_code == 422


def test_scan_rejects_invalid_source_type(client):
    response = client.post("/api/scan", json={"job_description": SCAM, "source_type": "pdf"})
    assert response.status_code == 422


def test_ollama_cannot_change_the_score(client):
    """The LLM path must be explanatory only."""
    plain = client.post("/api/scan", json={"job_description": SCAM, "company_name": "X"}).json()
    with_ai = client.post("/api/scan", json={
        "job_description": SCAM, "company_name": "X", "include_ai_explanation": True
    }).json()
    assert plain["risk_score"] == with_ai["risk_score"]
    assert plain["risk_level"] == with_ai["risk_level"]
    assert with_ai["ai_explanation"] is not None
    assert with_ai["ai_explanation"]["text"]


def test_storage_failure_still_returns_a_verdict(client, monkeypatch):
    """A database write error must not destroy a completed analysis."""
    from backend.database import crud

    def boom(*_args, **_kwargs):
        raise RuntimeError("database disk image is malformed")

    monkeypatch.setattr(crud, "create_scan", boom)
    response = client.post("/api/scan", json={"job_description": SCAM, "company_name": "X"})
    assert response.status_code == 200
    body = response.json()
    assert body["risk_score"] >= 75
    assert body["scan_id"] is None
    assert "storage_warning" in body


def test_url_scan_rejects_internal_hosts(client):
    response = client.post("/api/scan/url", json={"url": "http://127.0.0.1:8000/api/history"})
    assert response.status_code == 400
    assert "private" in response.json()["detail"].lower() or "loopback" in response.json()["detail"].lower()


def test_image_scan_rejects_non_image(client):
    response = client.post("/api/scan/image", files={"file": ("a.txt", b"nope", "text/plain")})
    assert response.status_code == 400


def test_rules_endpoint_lists_every_rule(client):
    body = client.get("/api/rules").json()
    assert body["count"] == len(get_rule_engine().rules)
    assert {"id", "flag", "severity", "weight"} <= set(body["rules"][0])


def test_money_mule_scheme_is_critical():
    """Regression: the rebuilt engine dropped this rule, scoring a laundering ad Medium."""
    text = (
        "Seeking trustworthy individuals to receive company vendor payments into their "
        "personal bank account and forward funds via Western Union. Earn 10% commission "
        "on every transaction processed."
    )
    result = get_rule_engine().analyze(text, company="International Investment Alliance")
    ids = {flag["id"]: flag for flag in result["flags"]}
    assert "MONEY_MULE" in ids
    assert ids["MONEY_MULE"]["severity"] == "CRITICAL"
    assert ids["MONEY_MULE"]["evidence"]


def test_reshiping_scheme_is_detected():
    text = (
        "Work from home receiving packages at your residential address, repackaging them "
        "and re-shipping parcels overseas with prepaid labels."
    )
    ids = [flag["id"] for flag in get_rule_engine().analyze(text, company="X")["flags"]]
    assert "MONEY_MULE" in ids
