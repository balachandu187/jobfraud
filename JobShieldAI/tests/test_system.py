"""
Automated system verification tests for JobShield AI.

Covers: dataset integrity, ML inference contract, every heuristic rule, risk floors,
the shared service pipeline, SQLite persistence/migration, URL-fetch SSRF guards and
the HTTP API surface.

Run from the JobShieldAI directory:
    python -m pytest tests/test_system.py -v
"""

import os
import sys
import tempfile

import pandas as pd
import pytest
from fastapi.testclient import TestClient

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database.db_manager import DatabaseManager  # noqa: E402
from model.predictor import JobPredictor  # noqa: E402
from model.train_model import prepare_text  # noqa: E402
from services import DetectionService, InputError, ScanPayload  # noqa: E402
from utils.detector import ScamDetector  # noqa: E402
from utils.explanation import get_safety_recommendations  # noqa: E402
from utils.risk_analyzer import RiskAnalyzer  # noqa: E402
from utils.url_fetcher import UrlFetchError, extract_readable_text, fetch_url_text  # noqa: E402

MODEL_DIR = os.path.join(BASE_DIR, "saved_models")
DATA_PATH = os.path.join(BASE_DIR, "data", "jobs.csv")

SCAM_TEXT = (
    "Congratulations! You are selected for a work-from-home job with a salary of ₹80,000 per month. "
    "Pay ₹2,000 registration fees to confirm your position. No interview required. "
    "Contact @FastCareersAdmin on Telegram."
)
GENUINE_TEXT = (
    "Software Developer position at ABC Technologies. Candidates should have Python, SQL and web "
    "development skills. Applicants will undergo a technical interview and credential verification. "
    "Apply through the company's official careers portal."
)
OTP_TEXT = (
    "Immediate hiring! Guaranteed job placement. Send your Aadhaar details, bank account "
    "information and OTP to complete registration."
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def predictor():
    return JobPredictor(model_dir=MODEL_DIR)


@pytest.fixture(scope="module")
def detector():
    return ScamDetector()


@pytest.fixture(scope="module")
def analyzer():
    return RiskAnalyzer()


@pytest.fixture()
def db():
    with tempfile.TemporaryDirectory() as tmp:
        yield DatabaseManager(db_path=os.path.join(tmp, "test.db"))


@pytest.fixture(scope="module")
def service():
    with tempfile.TemporaryDirectory() as tmp:
        yield DetectionService(model_dir=MODEL_DIR, db_path=os.path.join(tmp, "svc.db"))


@pytest.fixture(scope="module")
def client(service):
    import api

    original = api._service
    api._service = lambda: service
    try:
        yield TestClient(api.app)
    finally:
        api._service = original


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------
def test_dataset_exists_and_is_balanced():
    assert os.path.exists(DATA_PATH), "Run `python data/create_dataset.py` first."
    frame = pd.read_csv(DATA_PATH)
    counts = frame["fraudulent"].value_counts()
    assert len(frame) >= 120, "dataset should contain a meaningful number of postings"
    assert counts[0] == counts[1], "classes must be balanced"
    assert "archetype" in frame.columns, "grouped split key missing"


def test_dataset_has_no_duplicate_postings():
    frame = pd.read_csv(DATA_PATH)
    texts = prepare_text(frame)
    # Variants are allowed to differ, but exact duplicates signal lazy generation.
    assert texts.duplicated().sum() == 0


# ---------------------------------------------------------------------------
# Model artifacts
# ---------------------------------------------------------------------------
def test_artifacts_exist():
    assert os.path.exists(os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl"))
    assert os.path.exists(os.path.join(MODEL_DIR, "model.pkl"))


def test_predictor_is_ready(predictor):
    assert predictor.is_ready, predictor.load_error


def test_predictor_returns_valid_probabilities(predictor):
    result = predictor.predict(SCAM_TEXT)
    assert result["is_ready"] is True
    assert 0.0 <= result["fraud_probability"] <= 1.0
    assert result["prediction_label"] in ("Genuine", "Fraudulent")
    assert pytest.approx(result["fraud_probability"] + result["genuine_probability"], abs=1e-3) == 1.0


def test_predictor_handles_empty_and_odd_input(predictor):
    assert predictor.predict("")["fraud_probability"] == 0.0
    assert predictor.predict("   ")["is_ready"] is True
    assert predictor.predict("🙂🙂🙂")["is_ready"] is True
    assert predictor.predict("x" * 50000)["is_ready"] is True


def test_model_actually_separates_classes(predictor):
    """Regression: the shipped model previously scored a genuine job at 0.503 fraud."""
    genuine = predictor.predict(GENUINE_TEXT)["fraud_probability"]
    fraud = predictor.predict(SCAM_TEXT)["fraud_probability"]
    assert fraud > 0.70, f"scam posting scored only {fraud}"
    assert genuine < 0.50, f"genuine posting scored {genuine}"
    assert fraud - genuine > 0.30, "model has no usable separation between classes"


def test_predictor_degrades_without_artifacts():
    with tempfile.TemporaryDirectory() as tmp:
        blind = JobPredictor(model_dir=tmp)
        assert blind.is_ready is False
        result = blind.predict("anything")
        assert result["is_ready"] is False
        assert result["fraud_probability"] == 0.5  # neutral, not a fake verdict


# ---------------------------------------------------------------------------
# Heuristic rules
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "text,rule_id",
    [
        ("Pay ₹2,000 registration fee to confirm joining.", "UPFRONT_FEE"),
        ("Candidate must wire $250 visa processing charges.", "UPFRONT_FEE"),
        ("No interview required, direct joining letter issued.", "GUARANTEED_NO_INTERVIEW"),
        ("Share verification OTP and Aadhaar details.", "SENSITIVE_DATA_THEFT"),
        ("Receive client payments into your personal bank account and forward funds.", "MONEY_MULE_SCHEME"),
        ("Contact HR on Telegram @JobsAdmin.", "SUSPICIOUS_CHANNELS"),
        ("Mail your CV to hr.recruiter@gmail.com", "PERSONAL_EMAIL_DOMAIN"),
        ("Earn ₹80,000 per month for simple typing work from home.", "EXORBITANT_SALARY_LOW_SKILL"),
        ("Urgent hiring! Limited seats, apply within 24 hours.", "HIGH_PRESSURE_URGENCY"),
    ],
)
def test_each_rule_fires(detector, text, rule_id):
    result = detector.analyze(text=text, company="Some Company")
    assert rule_id in [warning["id"] for warning in result["warnings"]], result["warnings"]


def test_missing_company_is_flagged(detector):
    result = detector.analyze(text="Great job opportunity.", company="")
    assert "MISSING_COMPANY" in [warning["id"] for warning in result["warnings"]]


def test_clean_posting_triggers_no_rules(detector):
    result = detector.analyze(text=GENUINE_TEXT, company="ABC Technologies Ltd")
    assert result["warnings"] == [], result["warnings"]
    assert result["rule_score"] == 0


def test_rule_score_is_capped_at_100(detector):
    result = detector.analyze(text=SCAM_TEXT + " " + OTP_TEXT, company="X")
    assert 0 <= result["rule_score"] <= 100


# ---------------------------------------------------------------------------
# Risk analyzer
# ---------------------------------------------------------------------------
def test_critical_warning_enforces_high_risk_floor(analyzer):
    ml = {"fraud_probability": 0.02, "prediction_label": "Genuine", "is_ready": True}
    rules = {"rule_score": 10, "warnings": [{"id": "UPFRONT_FEE", "severity": "CRITICAL"}]}
    result = analyzer.calculate_risk(ml, rules)
    assert result["risk_score"] == 75
    assert result["risk_level"] == "High Risk"
    assert result["enforced_floor"] == 75


def test_high_severity_warning_prevents_low_risk(analyzer):
    ml = {"fraud_probability": 0.0, "prediction_label": "Genuine", "is_ready": True}
    rules = {"rule_score": 0, "warnings": [{"id": "GUARANTEED_NO_INTERVIEW", "severity": "HIGH"}]}
    result = analyzer.calculate_risk(ml, rules)
    assert result["risk_level"] == "Medium Risk"
    assert result["risk_score"] >= 45


def test_two_medium_warnings_prevent_low_risk(analyzer):
    ml = {"fraud_probability": 0.0, "prediction_label": "Genuine", "is_ready": True}
    rules = {
        "rule_score": 0,
        "warnings": [
            {"id": "PERSONAL_EMAIL_DOMAIN", "severity": "MEDIUM"},
            {"id": "HIGH_PRESSURE_URGENCY", "severity": "MEDIUM"},
        ],
    }
    assert analyzer.calculate_risk(ml, rules)["risk_score"] >= 45


def test_clean_input_stays_low_risk(analyzer):
    ml = {"fraud_probability": 0.05, "prediction_label": "Genuine", "is_ready": True}
    result = analyzer.calculate_risk(ml, {"rule_score": 0, "warnings": []})
    assert result["risk_level"] == "Low Risk"
    assert result["risk_score"] <= 10


def test_weights_are_normalised():
    analyzer = RiskAnalyzer(ml_weight=2, rule_weight=1)
    assert pytest.approx(analyzer.ml_weight + analyzer.rule_weight) == 1.0


def test_score_is_clamped_to_range(analyzer):
    ml = {"fraud_probability": 1.0, "prediction_label": "Fraudulent", "is_ready": True}
    result = analyzer.calculate_risk(ml, {"rule_score": 100, "warnings": []})
    assert result["risk_score"] == 100


# ---------------------------------------------------------------------------
# Safety advice
# ---------------------------------------------------------------------------
def test_every_rule_has_an_advisory():
    from utils.explanation import _ADVISORIES

    missing = [rule["id"] for rule in ScamDetector().rules if rule["id"] not in _ADVISORIES]
    assert missing == [], f"no advisory copy for: {missing}"


def test_advice_matches_warnings():
    tips = get_safety_recommendations(
        "High Risk", [{"id": "UPFRONT_FEE"}, {"id": "SENSITIVE_DATA_THEFT"}]
    )
    assert any("never transfer money" in tip.lower() for tip in tips)
    assert any("credentials" in tip.lower() for tip in tips)
    assert any("cybercrime.gov.in" in tip for tip in tips)


def test_low_risk_without_warnings_gives_verification_steps():
    tips = get_safety_recommendations("Low Risk", [])
    assert len(tips) == 3
    assert any("careers portal" in tip for tip in tips)


# ---------------------------------------------------------------------------
# Service pipeline
# ---------------------------------------------------------------------------
def test_service_scan_flags_scam(service):
    result = service.scan(ScanPayload(
        job_description=SCAM_TEXT,
        job_title="Work From Home Typist",
        company_name="FastCareers Online Services",
        contact_email="careers.recruitmentdesk@gmail.com",
        persist=False,
    )).to_dict()

    assert result["risk_result"]["risk_level"] == "High Risk"
    ids = [warning["id"] for warning in result["risk_result"]["warnings"]]
    assert "UPFRONT_FEE" in ids and "GUARANTEED_NO_INTERVIEW" in ids
    assert result["safety_tips"]


def test_service_scan_passes_genuine_job(service):
    result = service.scan(ScanPayload(
        job_description=GENUINE_TEXT,
        job_title="Software Developer",
        company_name="ABC Technologies Ltd",
        contact_email="talent@abctechnologies.com",
        persist=False,
    )).to_dict()
    assert result["risk_result"]["risk_level"] == "Low Risk"
    assert result["risk_result"]["warning_count"] == 0


def test_service_rejects_blank_input(service):
    with pytest.raises(InputError):
        service.scan(ScanPayload(job_description="   ", persist=False))


def test_service_persists_and_loads(service):
    result = service.scan(ScanPayload(
        job_description=OTP_TEXT, job_title="Back Office", company_name="Apex Global",
    ))
    assert result.scan_id and result.scan_id > 0
    record = service.db.get_scan(result.scan_id)
    assert record["job_title"] == "Back Office"
    assert record["risk_level"] == "High Risk"
    assert record["warnings"], "warnings should round-trip through SQLite"
    service.delete_scan(result.scan_id)


def test_service_records_url_provenance(service):
    result = service.scan(ScanPayload(
        job_description=SCAM_TEXT,
        source_url="https://careers-example.co/job/123",
        source_type="url",
    ))
    record = service.db.get_scan(result.scan_id)
    assert record["source_type"] == "url"
    assert record["source_url"] == "https://careers-example.co/job/123"
    service.delete_scan(result.scan_id)


def test_ollama_never_changes_the_verdict(service):
    """The LLM is explanatory only; a missing Ollama must not alter scores."""
    without = service.scan(ScanPayload(job_description=SCAM_TEXT, company_name="X", persist=False))
    with_ai = service.scan(ScanPayload(
        job_description=SCAM_TEXT, company_name="X", persist=False, include_ai_explanation=True,
    ))
    assert without.risk_result["risk_score"] == with_ai.risk_result["risk_score"]
    assert with_ai.ai_explanation is not None
    assert "text" in with_ai.ai_explanation


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def test_database_crud(db):
    scan_id = db.save_scan(
        job_text="Test Job Posting", prediction="Likely Genuine", risk_score=15,
        risk_level="Low Risk", job_title="QA Engineer", company_name="TestCorp",
    )
    assert scan_id > 0
    scans = db.get_recent_scans(limit=1)
    assert len(scans) == 1 and scans[0]["job_title"] == "QA Engineer"
    assert db.delete_scan(scan_id) is True
    assert db.delete_scan(scan_id) is False


def test_database_filters(db):
    db.save_scan(job_text="a", prediction="Suspicious", risk_score=50,
                 risk_level="Medium Risk", job_title="Data Entry", company_name="Acme")
    db.save_scan(job_text="b", prediction="Potentially Fraudulent", risk_score=90,
                 risk_level="High Risk", job_title="Typist", company_name="ScamCo")
    assert len(db.get_recent_scans(risk_level="High Risk")) == 1
    assert len(db.get_recent_scans(search="Acme")) == 1
    assert len(db.get_recent_scans()) == 2


def test_database_statistics(db):
    for score, level in ((10, "Low Risk"), (50, "Medium Risk"), (90, "High Risk")):
        db.save_scan(job_text="x", prediction="p", risk_score=score, risk_level=level,
                     warnings=[{"id": "UPFRONT_FEE", "title": "Upfront fee"}])
    stats = db.get_statistics()
    assert stats["total_scans"] == 3
    assert stats["average_risk_score"] == 50.0
    assert stats["top_warnings"][0]["count"] == 3
    assert len(stats["trend_7d"]) == 7


def test_database_migrates_legacy_schema():
    """A database created by the v1 build must not crash on the new columns."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "legacy.db")
        import sqlite3

        conn = sqlite3.connect(path)
        conn.execute(
            "CREATE TABLE scans (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,"
            " job_title TEXT, company_name TEXT, job_text TEXT NOT NULL, prediction TEXT NOT NULL,"
            " risk_score INTEGER NOT NULL, risk_level TEXT NOT NULL, warning_count INTEGER DEFAULT 0,"
            " warnings_json TEXT)"
        )
        conn.execute(
            "INSERT INTO scans (timestamp, job_text, prediction, risk_score, risk_level)"
            " VALUES ('2026-01-01 00:00:00', 'old row', 'Likely Genuine', 10, 'Low Risk')"
        )
        conn.commit()
        conn.close()

        manager = DatabaseManager(db_path=path)
        rows = manager.get_recent_scans()
        assert len(rows) == 1
        assert rows[0]["source_type"] == "text"
        assert manager.save_scan(
            job_text="new", prediction="Suspicious", risk_score=50,
            risk_level="Medium Risk", source_url="https://example.com",
        ) > 0


# ---------------------------------------------------------------------------
# URL extraction
# ---------------------------------------------------------------------------
def test_html_extraction_strips_chrome_and_scripts():
    html = """
    <html><head><title>Job</title><script>alert('x')</script></head>
    <body><nav>Home About</nav><article>
      <h1>Senior Backend Engineer</h1>
      <p>We are hiring a backend engineer with Python experience.</p>
      <p>Interviews will be scheduled with the engineering manager.</p>
    </article><footer>Copyright</footer></body></html>
    """
    text = extract_readable_text(html)
    assert "Senior Backend Engineer" in text
    assert "alert" not in text
    assert "Copyright" not in text
    assert "Home About" not in text


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:8000/api/history",
        "http://127.0.0.1/admin",
        "http://169.254.169.254/latest/meta-data/",
        "file:///etc/passwd",
        "ftp://example.com/job",
    ],
)
def test_url_fetcher_blocks_internal_and_non_http_targets(url):
    with pytest.raises(UrlFetchError):
        fetch_url_text(url)


# ---------------------------------------------------------------------------
# HTTP API
# ---------------------------------------------------------------------------
def test_api_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_api_status(client):
    payload = client.get("/api/status").json()
    assert payload["ml_ready"] is True
    assert payload["rules_loaded"] == 8
    assert "ollama_available" in payload


def test_api_scan_and_history_roundtrip(client):
    response = client.post("/api/scan", json={
        "job_title": "Typist",
        "company_name": "FastCareers",
        "contact_email": "hr.jobs@gmail.com",
        "job_description": SCAM_TEXT,
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["risk_result"]["risk_level"] == "High Risk"
    scan_id = body["scan_id"]

    listed = client.get("/api/history").json()
    assert any(row["id"] == scan_id for row in listed)
    assert client.get(f"/api/history/{scan_id}").status_code == 200
    assert client.delete(f"/api/history/{scan_id}").json()["success"] is True
    assert client.get(f"/api/history/{scan_id}").status_code == 404


def test_api_rejects_empty_description(client):
    response = client.post("/api/scan", json={"job_description": "   "})
    assert response.status_code == 422


def test_api_stats_shape(client):
    payload = client.get("/api/stats").json()
    for key in ("total_scans", "low_risk_count", "medium_risk_count", "high_risk_count",
                "average_risk_score", "top_warnings", "trend_7d"):
        assert key in payload


def test_api_rules_catalogue(client):
    rules = client.get("/api/rules").json()
    assert len(rules) == 8
    assert {"id", "severity", "weight"} <= set(rules[0])


def test_api_ollama_explain_falls_back(client):
    response = client.post("/api/ollama/explain", json={
        "job_title": "Typist", "risk_score": 80, "risk_level": "High Risk",
        "warnings": [{"title": "Upfront fee", "severity": "CRITICAL", "explanation": "Fees demanded."}],
    })
    assert response.status_code == 200
    assert response.json()["text"]


def test_api_url_scan_rejects_private_host(client):
    response = client.post("/api/scan/url", json={"url": "http://localhost:8000/api/history"})
    assert response.status_code == 400


def test_api_image_scan_rejects_non_image(client):
    response = client.post(
        "/api/scan/image",
        files={"file": ("note.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Network failure handling
# ---------------------------------------------------------------------------
def test_url_fetch_network_failure_is_a_400_not_a_500(client):
    """Regression: requests.SSLError/ConnectionError used to escape as HTTP 500."""
    response = client.post("/api/scan/url", json={"url": "https://nonexistent-host-xyz-abc.invalid"})
    assert response.status_code == 400
    assert "detail" in response.json()


def test_url_fetcher_raises_domain_error_not_raw_exception():
    with pytest.raises(UrlFetchError):
        fetch_url_text("https://nonexistent-host-xyz-abc.invalid")


# ---------------------------------------------------------------------------
# Storage resilience — the verdict must survive a broken audit log
# ---------------------------------------------------------------------------
def _corrupt_db(tmp_path):
    path = os.path.join(tmp_path, "corrupt.db")
    with open(path, "wb") as handle:
        handle.write(b"not a sqlite database" * 500)
    return path


def test_database_self_heals_when_file_is_corrupt(tmp_path):
    """A corrupt audit log must not prevent startup; the file is quarantined."""
    path = _corrupt_db(tmp_path)
    manager = DatabaseManager(db_path=path)
    assert manager.quarantined_path is not None, "original file should be preserved"
    assert os.path.exists(manager.quarantined_path)
    assert manager.health()["ok"] is True
    assert manager.get_statistics()["total_scans"] == 0
    assert manager.save_scan("t", "p", 10, "Low Risk") == 1


def test_scan_still_returns_a_verdict_when_storage_fails(monkeypatch):
    """Regression: a DB write error used to turn a completed scan into an HTTP 500."""
    from services import DetectionService

    service = DetectionService(model_dir=MODEL_DIR, db_path=os.path.join(tempfile.mkdtemp(), "x.db"))

    def boom(*_args, **_kwargs):
        raise RuntimeError("database disk image is malformed")

    monkeypatch.setattr(service.db, "save_scan", boom)
    result = service.scan(ScanPayload(job_description=SCAM_TEXT, company_name="X"))
    assert result.risk_result["risk_level"] == "High Risk"
    assert result.scan_id is None
    assert "storage_warning" in result.risk_result


def test_api_status_reports_storage_health(client):
    payload = client.get("/api/status").json()
    assert payload["storage"]["ok"] is True
