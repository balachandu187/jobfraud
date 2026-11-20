"""
Automated System Verification Tests for JobShield AI
Tests ML inference, rule-based heuristics, risk blending, and SQLite persistence.
"""

import os
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from api import GoogleAuthRequest, google_authenticate
from model.predictor import JobPredictor
from utils.detector import ScamDetector
from utils.risk_analyzer import RiskAnalyzer
from database.db_manager import DatabaseManager

@pytest.fixture(scope="module")
def setup_system():
    predictor = JobPredictor(model_dir="saved_models")
    detector = ScamDetector()
    analyzer = RiskAnalyzer()
    db = DatabaseManager(db_path="database/test_jobshield.db")
    return predictor, detector, analyzer, db

def test_artifacts_exist():
    assert os.path.exists("saved_models/tfidf_vectorizer.pkl"), "TF-IDF Vectorizer missing"
    assert os.path.exists("saved_models/model.pkl"), "Trained model missing"

def test_case_a_upfront_fee(setup_system):
    predictor, detector, analyzer, _ = setup_system
    text = (
        "Congratulations! You are selected for a work-from-home job with a salary of ₹80,000 per month. "
        "Pay ₹2,000 registration fees to confirm your position. No interview required."
    )
    ml_res = predictor.predict(text)
    rule_res = detector.analyze(text=text, company="")
    risk_res = analyzer.calculate_risk(ml_res, rule_res)

    assert risk_res["risk_level"] == "High Risk"
    assert risk_res["risk_score"] >= 70
    warning_ids = [w["id"] for w in risk_res["warnings"]]
    assert "UPFRONT_FEE" in warning_ids
    assert "GUARANTEED_NO_INTERVIEW" in warning_ids

def test_case_b_genuine_job(setup_system):
    predictor, detector, analyzer, _ = setup_system
    text = (
        "Software Developer position at ABC Technologies. Candidates should have Python, SQL, "
        "and web development skills. Applicants will undergo a technical interview. "
        "Apply through the company's official careers portal."
    )
    ml_res = predictor.predict(text)
    rule_res = detector.analyze(text=text, company="ABC Technologies")
    risk_res = analyzer.calculate_risk(ml_res, rule_res)

    assert risk_res["risk_level"] == "Low Risk"
    assert risk_res["risk_score"] <= 35
    assert risk_res["warning_count"] == 0

def test_case_c_sensitive_otp_theft(setup_system):
    predictor, detector, analyzer, _ = setup_system
    text = (
        "Immediate hiring! Guaranteed job placement. Send your Aadhaar details, "
        "bank account information, and OTP to complete registration."
    )
    ml_res = predictor.predict(text)
    rule_res = detector.analyze(text=text, company="")
    risk_res = analyzer.calculate_risk(ml_res, rule_res)

    assert risk_res["risk_level"] == "High Risk"
    assert risk_res["risk_score"] >= 75
    warning_ids = [w["id"] for w in risk_res["warnings"]]
    assert "SENSITIVE_DATA_THEFT" in warning_ids

def test_database_crud(setup_system):
    _, _, _, db = setup_system
    scan_id = db.save_scan(
        job_text="Test Job Posting for automated testing",
        prediction="Likely Genuine",
        risk_score=15,
        risk_level="Low Risk",
        job_title="QA Engineer",
        company_name="TestCorp"
    )
    assert scan_id > 0
    scans = db.get_recent_scans(limit=1)
    assert len(scans) == 1
    assert scans[0]["job_title"] == "QA Engineer"
    
    # Clean up test row
    deleted = db.delete_scan(scan_id)
    assert deleted is True

def test_google_auth_rejects_unverified_profile_payload():
    with pytest.raises(ValidationError):
        GoogleAuthRequest(email="person@example.com", name="Not verified by Google")

def test_google_auth_fails_when_client_id_is_missing(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)

    with pytest.raises(HTTPException) as error:
        google_authenticate(GoogleAuthRequest(id_token="unverified-token"))

    assert error.value.status_code == 503

