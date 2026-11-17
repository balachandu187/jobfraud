# JobShield AI — AI-Powered Fake Job and Recruitment Scam Detection System

![Python Version](https://img.shields.io/badge/Python-3.11-blue)
![Backend](https://img.shields.io/badge/Backend-FastAPI-009688)
![Frontend](https://img.shields.io/badge/Frontend-React%2019%20%2B%20Vite-61DAFB)
![ML Algorithm](https://img.shields.io/badge/ML-Logistic%20Regression-green)
![Feature Extraction](https://img.shields.io/badge/NLP-TF--IDF-purple)
![Database](https://img.shields.io/badge/Database-SQLite3-lightgrey)
![Local AI](https://img.shields.io/badge/Local%20LLM-Ollama-orange)
![Tests](https://img.shields.io/badge/Tests-56%20passing-brightgreen)

JobShield AI is a local, lightweight cybersecurity web application engineered to protect job seekers from predatory employment scams, advance-fee fraud, identity theft, and fake corporate recruitment campaigns.

**Input modes:** paste raw advertisement text, fill structured fields, give a URL for the server to fetch and extract, or upload a screenshot for OCR.

---

## 0. Quick start

One command builds what is missing and serves the UI **and** the API on a single port:

```bash
# macOS / Linux / WSL / Git Bash
cd JobShieldAI
./run.sh                    # add --no-build to skip the React build, --reload for dev
```

```powershell
# Windows PowerShell
cd JobShieldAI
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass   # once, if scripts are blocked
.\run.ps1                   # add -NoBuild / -Reload as needed
```

Then open **http://localhost:8000** (UI) and **http://localhost:8000/docs** (interactive API docs).

---

## 1. System architecture

The application implements a **dual-engine hybrid detection pipeline**, owned by a single
service layer (`services.py`) that both the REST API and the legacy Streamlit UI call — so the
detection logic cannot drift between front ends.

```text
        [ Job Advertisement Input: text | URL | screenshot ]
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
    [ Text extraction ]               [ Text extraction ]
     utils/url_fetcher.py              services.ocr_image()
     (SSRF-guarded)                    (Tesseract OCR)
              └───────────────┬───────────────┘
                              ▼
              ┌───────────────┴───────────────┐
              ▼                               ▼
    [ NLP Vectorizer (TF-IDF) ]     [ Heuristic Scam Detector ]
              │                               │
    [ Calibrated Logistic Regression ]  [ 8 Security Rules & Regex ]
      - Fraud probability                 - Upfront fees & deposits
      - Sigmoid-calibrated                - OTP / identity theft
              │                           - Money mule & reshipping
              │                           - Telegram / WhatsApp routing
              │                           - Free webmail recruiters
              │                           - Absurd pay for low skill
              │                           - False urgency
              │                           - Guaranteed no-interview hiring
              └───────────────┬───────────────┘
                              ▼
                 [ Ensemble Risk Analyzer ]
              50% ML + 50% rules, then safety floors:
              CRITICAL finding -> min 75 | HIGH -> min 45
              Tiers: Low (0-34) | Medium (35-65) | High (66-100)
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
    [ React 19 dark dashboard ]      [ SQLite audit trail ]
    - Risk gauge + engine bars       - Scan logs, filters, stats
    - Red-flag evidence              - URL / OCR provenance
    - Safety checklist               - Delete & purge
    - Optional local Ollama          - Legacy Streamlit UI (app.py)
```

### Repository layout

| Path | Purpose |
|---|---|
| `api.py` | FastAPI app — REST endpoints + serves the built React SPA |
| `services.py` | **Single** detection pipeline (ML → rules → risk → advice → DB) |
| `model/train_model.py` | Grouped-split training, calibration, metrics persistence |
| `model/predictor.py` | Inference with graceful degradation |
| `utils/detector.py` | 8-rule heuristic engine with evidence capture |
| `utils/risk_analyzer.py` | Weighted blend + safety floors + severity counts |
| `utils/explanation.py` | Per-rule safety advisories and reporting channels |
| `utils/url_fetcher.py` | SSRF-guarded URL → readable text extraction |
| `utils/ollama_client.py` | Optional local LLM narrative, never score-affecting |
| `database/db_manager.py` | SQLite with schema migration, filters, aggregates |
| `data/create_dataset.py` | 73-archetype balanced benchmark dataset generator |
| `tests/test_system.py` | 56 tests: rules, risk floors, API, DB migration, SSRF |
| `frontend/` | React 19 + Vite 8 + Tailwind 4 dashboard |
| `app.py` | Legacy Streamlit UI (optional; uses the same service layer) |

---

## 2. Setup from scratch

### Prerequisites
* Python 3.11+
* Node.js 20+ (only for the React UI)
* Tesseract OCR *(optional — only for screenshot scanning)*:
  [Windows installer](https://github.com/UB-Mannheim/tesseract/wiki) ·
  macOS `brew install tesseract` · Debian/Ubuntu `sudo apt install tesseract-ocr`

### Manual steps
```bash
cd JobShieldAI

# 1. Python dependencies
python -m pip install -r requirements.txt

# 2. Benchmark dataset (balanced, 73 archetypes)
python data/create_dataset.py

# 3. Train + persist model artifacts (writes saved_models/*.pkl)
python model/train_model.py

# 4. Automated tests
python -m pytest tests/test_system.py -v

# 5. Build the React UI
cd frontend && npm install && npm run build && cd ..

# 6. Serve UI + API together on port 8000
python api.py
```

### Frontend development mode
```bash
# terminal 1
python api.py                       # API on :8000

# terminal 2
cd frontend && npm run dev          # Vite on :5173, proxies /api -> :8000
```

### Configuration

| Variable | Default | Meaning |
|---|---|---|
| `JOBSHIELD_HOST` | `0.0.0.0` | Bind address |
| `JOBSHIELD_PORT` | `8000` | Port |
| `JOBSHIELD_RELOAD` | `0` | `1` enables uvicorn auto-reload |
| `JOBSHIELD_OLLAMA_URL` | `http://localhost:11434` | Ollama endpoint |
| `JOBSHIELD_OLLAMA_MODEL` | `llama3.2:latest` | Default model |
| `JOBSHIELD_OLLAMA_TIMEOUT` | `60` | Generation timeout (seconds) |
| `JOBSHIELD_CA_BUNDLE` | OS trust store | Custom CA file for URL fetching behind a proxy |

---

## 3. API reference

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Liveness probe (no DB or Ollama touch) |
| `GET` | `/api/status` | ML readiness, Ollama state, loaded rule IDs |
| `GET` | `/api/stats` | Totals, average score, top warnings, 7-day trend |
| `GET` | `/api/rules` | Heuristic rule catalogue |
| `GET` | `/api/history` | Audit log (`?limit=&risk_level=&search=`) |
| `GET` | `/api/history/{id}` | Single audit record |
| `DELETE` | `/api/history/{id}` | Delete one record |
| `DELETE` | `/api/history` | Purge all records |
| `POST` | `/api/scan` | Scan supplied text (JSON) |
| `POST` | `/api/scan/url` | Fetch a URL, then scan it |
| `POST` | `/api/scan/image` | OCR a screenshot (multipart), then scan |
| `POST` | `/api/extract` | Extraction only — no scoring, no DB write |
| `POST` | `/api/ollama/explain` | Local LLM narrative for an existing verdict |

```bash
curl -X POST http://localhost:8000/api/scan \
  -H 'Content-Type: application/json' \
  -d '{"job_title":"Typist","company_name":"FastCareers",
       "job_description":"Pay ₹2,000 registration fee. No interview required. Contact on Telegram."}'
```

---

## 4. Model card & reported metrics

Artifacts are regenerated by `python model/train_model.py`; metrics are written to
`saved_models/model_metrics.pkl`.

**Evaluation method matters.** The dataset contains several paraphrase variants of each job
archetype. Splitting rows at random leaks near-duplicate text into the test set and inflates
accuracy to a meaningless 100%. The trainer therefore splits **by archetype**
(`GroupShuffleSplit`), so the held-out set contains postings the model has never seen in any form.

| Metric (held-out, unseen archetypes) | Value |
|---|---|
| Accuracy | 96.4% |
| Precision | 100.0% |
| Recall (fraud class) | 93.3% |
| F1 | 96.6% |
| ROC-AUC | 1.000 |

* Dataset: 180 rows, 73 archetypes, exactly balanced 90 / 90.
* Train / test: 124 / 56 rows across 51 / 22 archetypes.
* Probabilities are sigmoid-calibrated (`CalibratedClassifierCV`) so a reported "70%" is
  approximately 70% — important because that number is blended directly into the risk score.
* The three held-out misses are variants of one deliberately hard case (a "Medical Billing
  Specialist" ad that imitates a real posting while demanding a software purchase fee).

**Why recall is the headline metric:** a false negative means a real scam reaches the user; a
false positive only sends a genuine job to manual verification. The `CRITICAL` safety floor
exists for the same reason — no confident ML score can override an explicit request for money,
OTPs or identity documents.

---

## 5. Benchmark behaviour

| Test case | Inputs | Engine findings | Verdict |
|---|---|---|---|
| **A. Upfront fee** | ₹80,000/mo typing job, ₹2,000 registration fee, no interview | `UPFRONT_FEE`, `GUARANTEED_NO_INTERVIEW`, `PERSONAL_EMAIL_DOMAIN` | **High Risk (75+)** |
| **B. Genuine tech role** | Software Developer, ABC Technologies, interview required | 0 red flags, ML fraud probability ≈ 0.19 | **Low Risk** |
| **C. Identity / OTP** | Guaranteed placement, demands Aadhaar + bank + OTP | `SENSITIVE_DATA_THEFT`, `GUARANTEED_NO_INTERVIEW` | **High Risk (75+)** |
| **D. Money mule** | "Receive client payments, forward via Western Union" | `MONEY_MULE_SCHEME` | **High Risk (75+)** |
| **E. Hard negative** | Real payroll / KYC role that legitimately mentions Aadhaar, PAN and bank details | 0 red flags (word-boundary patterns avoid false positives) | **Low Risk** |

Every rule carries a `severity`, a `weight`, and an `evidence` snippet quoting the matched
text, so a user can see exactly why a posting was flagged.

---

## 6. Security posture

* **SSRF protection** — URL fetching rejects non-HTTP schemes and any host resolving to a
  private, loopback, link-local, reserved or multicast address; every redirect hop is
  re-validated. Responses are capped at 2 MB / 10 s.
* **Parameterised SQL** throughout `DatabaseManager`; no user input is interpolated into SQL.
* **Upload limits** — screenshots capped at 8 MB, with content-type and image-decode validation.
* **Path traversal** — the SPA fallback resolves the path and confirms it stays inside `dist/`.
* **Local-only AI** — Ollama runs on the user's machine; no job text leaves it. If Ollama is
  absent, a deterministic template is used and the verdict is unchanged.
* **The LLM cannot alter verdicts** — enforced by construction (it receives a read-only
  summary) and covered by `test_ollama_never_changes_the_verdict`.

---

## 7. Optional local Ollama integration

1. Install [Ollama](https://ollama.com) and start it.
2. Pull a model: `ollama pull llama3.2` (or `gemma2:2b` for a lighter footprint).
3. Restart JobShield AI — `/api/status` reports `ollama_available: true` and the UI enables the
   **Enrich with Local Ollama AI** toggle.

The narrative never changes the score, the tier, or the warning list.

---

## 8. Legacy Streamlit UI

`app.py` is still supported and now delegates to the same `services.py` pipeline:

```bash
python -m streamlit run app.py     # http://localhost:8501
```

It is optional — the React UI and REST API do not depend on Streamlit.

---

## 9. College project & technical interview guide

### Project abstract
Recruitment scams have surged with the rise of remote work, causing financial extortion and
identity theft among job applicants. **JobShield AI** is an offline-capable verification system
combining NLP machine learning with deterministic cybersecurity rules to evaluate job postings,
quantify threat probability on a 0–100 scale, and provide actionable defensive measures. It
accepts pasted text, URLs and screenshots.

### Problem statement
Unemployed candidates and fresh graduates are targeted by criminals impersonating recruiters on
LinkedIn, Telegram and WhatsApp. Traditional spam filters only inspect email, leaving job boards
and social listings unvetted. Job seekers need a transparent, explainable tool to audit an offer
before paying money or handing over credentials.

### Existing system vs. proposed system

| Dimension | Existing approaches | JobShield AI |
|---|---|---|
| **Technique** | Keyword blocklists or black-box classifiers | Hybrid ensemble (TF-IDF + Logistic Regression + 8 rule engines) |
| **Explainability** | Opaque score | Per-flag severity, weight and quoted evidence |
| **Safety overrides** | Averages away severe signals | Severity floors (CRITICAL ⇒ ≥ 75) |
| **Input types** | Text only | Text, URL, screenshot (OCR) |
| **Privacy & cost** | Paid third-party cloud APIs | 100% offline, local SQLite, optional local Ollama |
| **Resource usage** | Heavy cloud infrastructure | Runs on 8 GB RAM / Windows 11 |

---

## 10. Top 20 viva / interview questions

**Q1: Why Logistic Regression instead of deep learning (e.g. BERT)?**
*Fast inference, under 100 MB of RAM, trains in seconds on a laptop, and produces calibrated
probabilities directly — no GPU needed and fully interpretable.*

**Q2: What is TF-IDF and why use n-grams (1, 2)?**
*TF-IDF balances term frequency against corpus rarity. Unigrams catch keywords ("fee",
"telegram"); bigrams catch deceptive phrases ("registration fee", "no interview").*

**Q3: Why not rely solely on the ML model?**
*Models can miss adversarial or novel wording. The rule engine is a deterministic safety net for
non-negotiable red flags such as OTP or deposit requests.*

**Q4: How is the composite risk score computed?**
*`0.5 × ML probability + 0.5 × rule score`, then a severity floor: any CRITICAL finding locks
the score to at least 75 (High Risk).*

**Q5: Why split by archetype instead of by row?**
*The dataset contains paraphrase variants of each posting. A random row split puts near-duplicates
in both train and test, which produced a bogus 100% accuracy in the earlier build. Grouped
splitting reports performance on genuinely unseen postings (96.4% accuracy, 93.3% recall).*

**Q6: What is probability calibration and why does it matter here?**
*`CalibratedClassifierCV` (sigmoid) maps raw decision scores onto observed frequencies. Since the
fraud probability is blended straight into a user-facing risk score, an uncalibrated 0.7 would
silently distort the verdict.*

**Q7: How does the model handle class imbalance?**
*`class_weight='balanced'` reweights classes inversely to their frequency, and the dataset is
generated balanced by construction.*

**Q8: Which metric is prioritised and why?**
*Recall and F1 on the fraudulent class. A false negative lets a real scam through; a false
positive only triggers manual verification.*

**Q9: How is SQLite used?**
*An embedded, zero-configuration store for every scan: timestamp, title, company, score, tier,
warnings JSON, and provenance (source URL / OCR). It powers history, statistics and the trend chart.*

**Q10: How is SQL injection prevented?**
*All queries use parameterised `?` placeholders; no user input is string-formatted into SQL.*

**Q11: How does the schema survive upgrades?**
*`PRAGMA user_version` plus an `ALTER TABLE ... ADD COLUMN` migration runs on startup, so a
database created by the older build keeps working — verified by
`test_database_migrates_legacy_schema`.*

**Q12: What stops the URL feature from becoming an SSRF vulnerability?**
*Scheme allow-list (http/https), DNS resolution checked against private, loopback, link-local and
reserved ranges, redirects re-validated per hop, and size/time caps.*

**Q13: How is Ollama kept optional?**
*A 1.5 s health check with a deterministic template fallback. If the configured model is missing,
the response tells the user which `ollama pull` command to run.*

**Q14: Can the LLM change the verdict?**
*No. It only receives a read-only summary of an already-computed verdict. A regression test
asserts the score is identical with and without the LLM.*

**Q15: How does OCR integrate?**
*Uploaded screenshots are decoded server-side and passed to Tesseract; the extracted text then
enters the same pipeline. A missing Tesseract binary returns a clear 400 rather than a crash.*

**Q16: How does the frontend stay consistent with the backend?**
*One service layer (`services.py`) is called by both FastAPI and Streamlit, so ML, rules, risk
scoring and advice exist in exactly one place.*

**Q17: What happens on empty or one-line input?**
*Pydantic validates the request (422), the service raises a domain `InputError` (400), and the
predictor returns neutral probabilities for degenerate text instead of raising.*

**Q18: What is an advance-fee recruitment scam?**
*A scheme offering attractive employment conditional on paying upfront for registration,
training kits, uniform gate passes or software.*

**Q19: What is a money-mule / reshipping scam?**
*Victims are hired as "payment processing agents" to receive and forward laundered funds, or to
receive and re-ship parcels bought with stolen cards — both make the victim criminally liable.*

**Q20: What are the limitations and next steps?**
*No live WHOIS/domain-age lookup or company-registry verification yet, and the dataset is
synthetic (modelled on EMSCAD). Next: domain-age checks, a browser extension, and a larger
real-world corpus.*

---

## 11. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "FastAPI Disconnected" badge | API not running | Start `python api.py` — the UI is served from the same origin |
| ML shows "Model Not Trained" | Artifacts missing | `python data/create_dataset.py && python model/train_model.py` |
| Screenshot scan: "Tesseract OCR binary not found" | OCR engine absent | Install Tesseract (see Prerequisites) |
| URL scan: "Refusing to fetch a private or loopback address" | Target is local/private | Paste the text directly — this guard prevents SSRF |
| URL scan: TLS error | Corporate proxy or stale CA bundle | Set `JOBSHIELD_CA_BUNDLE` to your CA file |
| "Ollama query timed out" | Model not pulled or too slow | `ollama pull llama3.2`, or leave the toggle off |

---

## 12. Disclaimer

JobShield AI produces an automated risk estimate. It is **not** legal proof that an organisation
is fraudulent. Always verify a job offer independently through official channels, and report
suspected fraud to cybercrime.gov.in or 1930 in India.
