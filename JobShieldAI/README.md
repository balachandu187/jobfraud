# JobShield AI — AI-Powered Fake Job and Recruitment Scam Detection System

![Python Version](https://img.shields.io/badge/Python-3.11-blue)
![Framework](https://img.shields.io/badge/Frontend-Streamlit-red)
![ML Algorithm](https://img.shields.io/badge/ML-Logistic%20Regression-green)
![Feature Extraction](https://img.shields.io/badge/NLP-TF--IDF-purple)
![Database](https://img.shields.io/badge/Database-SQLite3-lightgrey)
![Local AI](https://img.shields.io/badge/Local%20LLM-Ollama-orange)

JobShield AI is a local, lightweight cybersecurity web application engineered to protect job seekers from predatory employment scams, advance-fee fraud, identity theft, and fake corporate recruitment campaigns.

---

## 1. System Architecture

The application implements a **Dual-Engine Hybrid Detection Pipeline**:

```text
               [ Job Advertisement Input ]
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
    [ NLP Vectorizer (TF-IDF) ]   [ Heuristic Scam Detector ]
              │                           │
    [ Logistic Regression ]       [ 8 Security Rules & Regex ]
      - Fraud Probability           - Upfront Fees & Deposits
      - Class Probability           - Identity & OTP Theft
              │                     - Generic Personal Webmail
              │                     - Telegram/WhatsApp Redirection
              │                     - High-Pressure False Urgency
              └─────────────┬─────────────┘
                            ▼
               [ Ensemble Risk Analyzer ]
             Blended Composite Risk Score (0 - 100)
             Risk Tiers: Low Risk | Medium Risk | High Risk
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
    [ Streamlit Dark UI Dashboard ]  [ SQLite Audit Trail ]
    - Plotly Risk Visualizer         - Scan Logs & Metrics
    - Explainable Safety Actions     - Deletion & Management
    - Optional Local Ollama LLM
```

---

## 2. Windows PowerShell Setup & Run Guide

All commands run inside Windows PowerShell in the project directory:

### Step 1: Open PowerShell and Navigate to Project
```powershell
cd C:\Users\ADMIN\Downloads\jobfraud\JobShieldAI
```

### Step 2: Activate the Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell restricts script execution, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Generate the Benchmark Dataset
```powershell
python data\create_dataset.py
```

### Step 5: Train & Persist the ML Model
```powershell
python model\train_model.py
```
*Outputs serialized vectorizer and model into `saved_models/`.*

### Step 6: Run Automated Tests
```powershell
pytest tests\test_system.py -v
```

### Step 7: Launch the Streamlit Web Application
```powershell
streamlit run app.py
```
The application will open automatically in your browser at `http://localhost:8501`.

### Deploy the React + FastAPI Preview to Render

The repository includes a Render Blueprint and a Dockerfile that build and serve
the React frontend together with FastAPI. To deploy:

1. Push the repository to GitHub.
2. In Render, choose **New → Blueprint** and select this repository. Render reads
   the root `render.yaml` and creates the `jobshield-ai` web service.
3. In the service's environment settings, set `GOOGLE_CLIENT_ID` to your Google
   OAuth **Web application** client ID. Do not add a Google client secret; this
   sign-in flow verifies ID tokens on the backend and does not use a client secret.
4. Wait for the service health check at `/api/status` to pass, then open the
   `onrender.com` URL shown in the Render dashboard.
5. In Google Cloud Console, add that URL's origin (for example,
   `https://jobshield-ai.onrender.com`) to **Authorized JavaScript origins**.
   The popup flow does not need an Authorized redirect URI.

The Blueprint generates `JOBSHIELD_SECRET_KEY` for the service. The free Render
plan may sleep when idle, and its filesystem is temporary; SQLite records are
not guaranteed to persist across restarts or redeployments.

---

## 3. Optional Local Ollama AI Integration

To use local natural language explanations via Ollama:
1. Download Ollama for Windows from [ollama.com](https://ollama.com).
2. Open a separate terminal and run a lightweight model:
   ```powershell
   ollama run llama3.2:latest
   ```
   *(Or `ollama run gemma:2b` for an ultra-lightweight 2 GB footprint)*
3. When Ollama is running, JobShield AI detects it automatically on `http://localhost:11434` and unlocks the **Local AI Synthesis** tab on the Scan Results page.

---

## 4. Benchmark Test Evaluation

| Test Case | Inputs | Engine Findings | Classification |
|---|---|---|---|
| **Case A (Upfront Fee)** | ₹80,000/mo typing job, ₹2,000 registration fee, no interview required. | Flags `UPFRONT_FEE`, `GUARANTEED_NO_INTERVIEW` | **High Risk (Potentially Fraudulent)** |
| **Case B (Genuine Tech Role)** | Software Developer at ABC Technologies, technical interview required, official careers portal. | High genuine ML probability, 0 heuristic red flags | **Low Risk (Likely Genuine)** |
| **Case C (Identity / OTP Scam)** | Guaranteed placement, demands Aadhaar, bank passbook, and OTP. | Flags `SENSITIVE_DATA_THEFT`, `SUSPICIOUS_CHANNELS` | **High Risk (Potentially Fraudulent)** |

---

## 5. College Project & Technical Interview Guide

### Project Abstract
Recruitment scams have surged dramatically with the rise of remote work, leading to financial extortion and identity theft among unsuspecting job applicants. **JobShield AI** is an intelligent, offline-capable verification system combining NLP machine learning and deterministic cybersecurity rules to evaluate job postings, quantify threat probability on a 0-100 scale, and provide actionable defensive measures.

### Problem Statement
Unemployed candidates and fresh college graduates are vulnerable to cybercriminals impersonating legitimate recruiters on portals like LinkedIn, Telegram, and WhatsApp. Traditional spam filters only inspect emails, leaving posted job descriptions and social media listings unvetted. Job seekers require a transparent, explainable tool to audit job offers prior to submitting money or credentials.

### Existing System vs. Proposed System

| Dimension | Existing Approaches | JobShield AI (Proposed System) |
|---|---|---|
| **Technique** | Pure keyword blocklists or black-box classifiers | Hybrid Ensemble (TF-IDF + Logistic Regression + 8 Rule Engines) |
| **Explainability** | Opaque score without justification | Detailed breakdown of each red flag with safety advice |
| **Safety Overrides** | Averages away high-danger signals | Critical severity floor (e.g. OTP/fee flags guarantee High Risk) |
| **Privacy & Cost** | Requires paid third-party cloud APIs | 100% offline, local SQLite, optional local Ollama LLM |
| **Resource Usage** | Heavy enterprise cloud infrastructure | Lightweight: runs smoothly on 8 GB RAM and Windows 11 |

---

## 6. Top 20 Technical Viva / Interview Questions & Answers

**Q1: Why did you choose Logistic Regression instead of deep learning (e.g., BERT)?**  
*Answer:* Logistic Regression coupled with TF-IDF provides high inference speed, minimal memory overhead (<100 MB RAM), and native calibrated probabilistic outputs (`predict_proba`). On an 8 GB RAM local machine, it trains in seconds and provides complete interpretability without GPU overhead.

**Q2: What is TF-IDF and why use n-grams (1, 2)?**  
*Answer:* TF-IDF (Term Frequency - Inverse Document Frequency) balances how frequently a term appears against how rare it is across the entire corpus. Unigrams capture single keywords (`fee`, `telegram`), while bigrams capture deceptive phrases (`registration fee`, `no interview`, `daily payout`).

**Q3: Why not rely solely on the Machine Learning model?**  
*Answer:* ML models can suffer from false negatives when scammers use adversarial prompt engineering or novel wording. The rule-based engine acts as a deterministic safety net for non-negotiable red flags like requests for OTPs or registration deposits.

**Q4: How does the composite risk scoring algorithm work?**  
*Answer:* The base score is computed as `(ML Probability * 50%) + (Rule Score * 50%)`. However, if any `CRITICAL` severity rule triggers (such as upfront fees or bank OTP requests), a safety floor is applied, locking the minimum risk score to 75 (High Risk).

**Q5: How does JobShield AI handle class imbalance in recruitment datasets?**  
*Answer:* We configure `class_weight='balanced'` in scikit-learn's Logistic Regression, which automatically adjusts weights inversely proportional to class frequencies, ensuring fraudulent cases are not penalized during gradient optimization.

**Q6: What role does SQLite play in this architecture?**  
*Answer:* SQLite serves as an embedded, zero-configuration relational database storing scan records, timestamps, risk scores, and warning logs to enable history auditing, dashboard analytics, and trend visualization.

**Q7: How is Ollama integrated without making it a hard dependency?**  
*Answer:* The `OllamaClient` performs a non-blocking health check against `http://localhost:11434/api/tags` with a 1.5-second timeout. If unreachable or disabled, the application uses deterministic template-based explanations, ensuring uninterrupted availability.

**Q8: Can the language model alter the risk score or ML verdict?**  
*Answer:* No. The system architecture enforces strict separation of concerns: the LLM is purely explanatory. Scores and classifications are computed strictly by the deterministic analyzer and ML pipeline.

**Q9: What metric is prioritized during model evaluation?**  
*Answer:* Recall and F1-score for the Fraudulent class (`fraudulent = 1`). In cybersecurity, false negatives (failing to identify a real scam) are significantly more dangerous than false positives (flagging a genuine job for manual inspection).

**Q10: What are the main limitations of the current prototype?**  
*Answer:* It relies on text provided by the user and does not yet query live corporate domain registries, WHOIS records, or company registry databases.

**Q11: What are future enhancements for JobShield AI?**  
*Answer:* Adding automated URL/domain WHOIS age lookup, Chrome extension overlay on job boards (LinkedIn, Indeed), and OCR image ingestion for screenshot scanning.

**Q12: Why is generic webmail (@gmail.com) considered a risk factor?**  
*Answer:* Legitimate corporate recruiters possess email addresses tied to authenticated domain names configured with SPF, DKIM, and DMARC records. Generic free emails indicate lack of verified corporate affiliation.

**Q13: How does sublinear TF scaling in TfidfVectorizer improve performance?**  
*Answer:* `sublinear_tf=True` replaces term frequency $tf$ with $1 + \log(tf)$, dampening the effect of repeated words so an advertisement repeating a keyword ten times is not ten times more important.

**Q14: How does the application prevent SQL injection?**  
*Answer:* All SQLite database interactions in `DatabaseManager` use parameterized queries (`?` placeholders) rather than raw string formatting.

**Q15: Why is Streamlit suited for this project?**  
*Answer:* Streamlit connects Python backend data pipelines directly to interactive reactive UI components, supporting rapid prototyping, state management, and real-time Plotly charts without requiring a separate JavaScript frontend.

**Q16: What happens if an applicant pastes an empty or one-line string?**  
*Answer:* Input validation verifies string length, and `JobPredictor` handles edge cases by providing defensive defaults rather than throwing uncaught exceptions.

**Q17: What is an advance-fee scam in recruitment?**  
*Answer:* A scheme where the perpetrator offers attractive employment conditional on the applicant paying money in advance for background checks, training kits, uniform gates, or software tools.

**Q18: What is a money mule recruitment scam?**  
*Answer:* Fraud where victims are hired as "payment processing agents" to receive stolen or laundered funds into their personal bank accounts and wire them elsewhere, making the victim criminally liable.

**Q19: How are model artifacts preserved across app restarts?**  
*Answer:* Scikit-learn models and vectorizers are serialized using `joblib.dump()` into `saved_models/` and loaded into Streamlit session state on startup.

**Q20: What is the benefit of offline local AI execution?**  
*Answer:* Total privacy (sensitive resume and contact data never leaves the user's computer), zero API subscription costs, and guaranteed uptime without external internet dependencies.

