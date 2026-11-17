# JobShield AI — Demo Runbook & Interview Prep

Everything below was executed against the running app on 2026-11-17. The numbers are
real output, not estimates. Re-run `python scripts/seed_demo.py` any time to reproduce them.

---

## 0. Ten minutes before the interview

```bash
cd JobShieldAI
python -m pip install -r requirements.txt      # once
python scripts/seed_demo.py                    # fills the dashboard with 5 real records
./run.sh --no-build                            # or: .\run.ps1 -NoBuild on Windows
```

Then verify, in this order:

| Check | Command / action | Expected |
|---|---|---|
| UI loads | open `http://localhost:8000` | Dark dashboard, **5 total scans**, avg 54.8 |
| API alive | open `http://localhost:8000/api/health` | `{"status":"ok"}` |
| Model loaded | open `http://localhost:8000/api/status` | `"ml_ready": true`, `"rules_loaded": 8` |
| Storage healthy | same response | `"storage": {"ok": true, ...}` |
| Tests green | `python -m pytest -q` | `59 passed` |

**If the UI is blank:** run `cd frontend && npm install && npm run build`. If you skip that,
the API now serves a page telling you exactly this instead of a 404 — the demo is not dead.

**If the ML says "Model Not Trained":** `python data/create_dataset.py && python model/train_model.py`.

---

## 1. The 6-minute demo script

Open on the **Home Dashboard** and say one sentence:

> "Recruitment fraud targets fresh graduates with fake job ads that ask for a registration fee
> or an OTP. Existing spam filters only read email, so job-board posts go unvetted. JobShield AI
> scores any job ad 0–100 using two independent engines, and shows exactly why."

### Beat 1 — Scam ad (60 s)  ⭐ the money shot

Job Scanner → click preset **🚨 Upfront Fee Scam** → **Run Dual-Engine Security Scan**.

Real result you will see:

| Field | Value |
|---|---|
| Risk score | **82 / 100 — High Risk — "Potentially Fraudulent"** |
| ML fraud probability | **0.884** (88.4%) |
| Rule score | **75 / 100** |
| Blended | 81.7 |
| Safety floor | `CRITICAL warning -> floor 75` |

Flags shown, each with quoted evidence:

- `CRITICAL` **Upfront / Registration Fee Demanded** — evidence `"Pay ₹2,000"`
- `HIGH` **Guaranteed Hiring Without Proper Screening** — evidence `"No interview required"`
- `MEDIUM` **Generic Free Webmail Used for Recruitment** — `careers.recruitmentdesk@gmail.com`

Point at the **evidence string**. That is the answer to "how is this explainable?" — the user
sees the exact words that triggered each rule.

### Beat 2 — Genuine job (40 s)

Click preset **🛡️ Genuine Tech Role** → scan.

| Field | Value |
|---|---|
| Risk score | **10 / 100 — Low Risk — "Likely Genuine"** |
| ML fraud probability | **0.203** |
| Rule score | **0** |
| Flags | none |

Say: *"The ML engine is not just a keyword matcher — this posting contains the words 'salary',
'interview' and 'portal', and still scores near zero."*

### Beat 3 — The one that proves it is not just keyword matching (60 s) ⭐⭐

Click **Job Scanner → Raw Text**, paste this genuine payroll ad and scan:

```
As part of statutory onboarding you will collect and verify new-joiner bank account
details and PAN/Aadhaar documentation, then upload them to the client HRMS under our
ISO 27001 policy. B.Com with 3 years payroll compliance experience. Candidates complete
background verification after a written offer is signed.
```

| Field | Value |
|---|---|
| Risk score | **9 / 100 — Low Risk** |
| ML probability | 0.175 |
| Flags | **0** — despite containing "bank account", "Aadhaar", "PAN" |

This is your hardest-hitting point. A naive keyword system flags this as identity theft. Yours
does not, because the rules use word-boundary patterns that require an *instruction to send*
documents, not a *mention* of them. Most student projects fail exactly here.

### Beat 4 — OTP scam (40 s)

Preset **⚠️ OTP & Identity Scam** → scan → **98 / 100, five flags**:

`SENSITIVE_DATA_THEFT` (CRITICAL, `"Send Aadhaar"`), `GUARANTEED_NO_INTERVIEW`,
`SUSPICIOUS_CHANNELS`, `PERSONAL_EMAIL_DOMAIN`, `HIGH_PRESSURE_URGENCY`.

### Beat 5 — URL + security (40 s)

Job Scanner → **From URL** tab → paste `https://github.com/balachandu187/jobfraud` → **Fetch URL & Scan**.
It fetches, strips nav/scripts, extracts 326 characters, and scores it.

Then paste `http://169.254.169.254/latest/meta-data/` → the API refuses:

> "Refusing to fetch a private or loopback address. Paste the advertisement text directly instead."

Say: *"A URL feature is an SSRF vulnerability if you build it naively. This one blocks private,
loopback and link-local addresses and re-validates every redirect hop."*

### Beat 6 — Audit trail (30 s)

**Scan Audit Logs** → filter by *High Risk*, expand a row, delete a record.
**Home Dashboard** → the donut, top-warning breakdown and 7-day trend update.

Say: *"Every verdict is persisted to SQLite with its warnings as JSON, so an audit trail exists."*

### Beat 7 — Close (20 s)

> "Fifty-nine automated tests cover every rule, both safety floors, the database migration,
> the SSRF guards and the whole HTTP surface. It runs fully offline — no cloud API, no data
> leaves the machine."

---

## 2. Numbers you must know cold

**Model (held-out, unseen archetypes):**

| Metric | Value |
|---|---|
| Accuracy | 96.4% |
| Precision | 100.0% |
| Recall (fraud) | 93.3% |
| F1 | 96.6% |
| ROC-AUC | 1.000 |

Dataset: 180 rows, 73 archetypes, exactly balanced 90/90. Split 124 train / 56 held-out, by
**archetype**.

**Scoring:** `0.5 × ML_probability + 0.5 × rule_score`, then floors —
CRITICAL finding ⇒ min 75; HIGH ⇒ min 45; two MEDIUM ⇒ min 45. Tiers: 0–34 Low, 35–65 Medium, 66–100 High.

**Stack:** Python 3.11 · FastAPI · scikit-learn (TF-IDF + calibrated Logistic Regression) ·
React 19 + Vite + Tailwind · SQLite · optional local Ollama.

**Scale:** 8 heuristic rules · 59 tests · 13 API endpoints.

---

## 3. Questions you will almost certainly get

**"Why not use BERT or a deep learning model?"**
> "Three reasons. It trains in seconds on a laptop CPU with no GPU, it uses under 100 MB of RAM,
> and it gives calibrated probabilities I can feed straight into a risk score. On a 180-row
> dataset BERT would overfit badly and I could not explain a single coefficient. If the dataset
> grew to 50,000 real postings I would revisit that."

**"Your dataset is synthetic. Doesn't that invalidate the accuracy?"**
> "Yes for real-world claims — I say so explicitly in the README. The dataset is modelled on
> EMSCAD patterns and exists to prove the pipeline works. What transfers is the architecture and
> the rule engine; the 96.4% is a measure of this dataset, not of deployment performance."
> ⭐ *Conceding this cleanly scores far better than defending it.*

**"You report 100% precision. Isn't that suspicious?"**
> "It is, and it is a limitation of a small held-out set — 56 rows, 30 of them fraud. One false
> positive would drop precision to 96%. The metric I actually optimise is recall, because a false
> negative means a real scam reaches the user, while a false positive only sends a genuine job to
> manual review."

**"How do you know you are not overfitting?"**
> "Two checks. First, the train/test split is grouped by archetype, so no paraphrase variant of a
> test posting ever appears in training — a row-level split gave me a fake 100% before I fixed it.
> Second, the trainer prints training-set metrics next to held-out ones; the gap is 100% vs 96.4%."

**"What's the ML weight vs rule weight, and why?"**
> "50/50. The ML engine generalises to unseen phrasing but can be fooled by adversarial wording;
> the rule engine is deterministic but brittle on novel scams. Blending covers both failure modes.
> The weights are constructor parameters, so it's one line to change."

**"What if the model is confident but a rule fires?"**
> "The floors win. Any CRITICAL finding — money requested, OTP requested — locks the score to at
> least 75 regardless of ML output. Demonstrated in the money-mule case: blended was 71.4, the
> floor pushed it to 75."

**"How does the LLM fit in? Can it change the verdict?"**
> "It cannot, by construction. Ollama receives a read-only summary of an already-computed verdict
> and only writes prose. There is a test — `test_ollama_never_changes_the_verdict` — that asserts
> the score is identical with and without it. If Ollama is absent, a deterministic template is
> used and the app keeps working."

**"What happens if two people scan at once?"**
> "FastAPI runs sync endpoints in a thread pool, and each DB call opens its own short-lived SQLite
> connection with WAL mode, so readers do not block the writer. Beyond demo scale I would move to
> Postgres."

**"How is the frontend kept in sync with the backend?"**
> "One service layer, `services.py`, is imported by both the FastAPI routes and the legacy
> Streamlit app. The detection logic exists in exactly one place, so the two UIs cannot drift."

**"What was the hardest bug?"**
> "The model scored a genuine engineering job at 0.503 — a coin flip. The cause was that the
> dataset was ten archetypes duplicated five times, so the classifier memorised exact strings and
> learned nothing transferable. I rebuilt the dataset to 73 archetypes, including 'hard negatives'
> — real payroll and KYC roles that legitimately mention Aadhaar and bank details — and added
> probability calibration. The genuine case dropped to 0.203."
> ⭐ *Pick this one. It shows you can diagnose rather than just pile on features.*

**"What would you do with another month?"**
> "Three things in priority order. First, WHOIS/domain-age lookup on the recruiter's domain —
> it's the one signal a scammer cannot fake cheaply. Second, a real corpus instead of synthetic
> data, with proper cross-validation. Third, a browser extension so it works where people
> actually read job posts."

---

## 4. Live-coding questions to expect

**"Add a new rule."** In `utils/detector.py`, append to `self.rules`:

```python
{
    "id": "CRYPTO_TASK_SCAM",
    "category": "Financial Scam",
    "severity": "CRITICAL",
    "weight": 35,
    "pattern": re.compile(r"usdt|tronlink|crypto task|recharge your wallet", re.IGNORECASE),
    "title": "Crypto Task / Wallet Recharge Scam",
    "explanation": "Task scams require victims to deposit crypto before unlocking payouts.",
},
```

Then add matching copy in `utils/explanation.py` `_ADVISORIES` — there is a test
(`test_every_rule_has_an_advisory`) that will fail if you forget, which is a nice thing to
mention out loud.

**"Why does `min_df=1` matter here?"** Because the vocabulary is small (180 documents); raising
it would drop the rare fraud phrases that carry the signal.

**"Change the risk threshold to 40."** One line in `utils/risk_analyzer.py` — but note the
floors are separate constants (`CRITICAL_FLOOR`, `ELEVATED_FLOOR`) and must move too.

**"Return the matched substring."** Already done — every warning carries `evidence`.

---

## 5. Fallbacks if something breaks live

| Problem | Say this | Do this |
|---|---|---|
| UI blank | "The production bundle isn't built on this machine." | `cd frontend && npm install && npm run build`, or use `/docs` |
| Model not loaded | — | `python model/train_model.py` (takes ~1 s) |
| Screenshot tab errors | "OCR needs the Tesseract binary installed — the API returns a clear 400 rather than crashing." | Skip Beat 5's OCR; URL scan still works |
| Ollama offline | "Fully expected — the toggle degrades to a deterministic template." | Leave the toggle off |
| Port 8000 busy | — | `JOBSHIELD_PORT=8080 ./run.sh --no-build` |
| Total failure | — | Show `/docs`, run `python -m pytest -q` (59 passed), walk the architecture section of the README |

**Always have `python -m pytest -q` ready.** "59 passed" on screen is the strongest possible
answer to "how do you know it works?"

---

## 6. Things not to claim

- ❌ "It detects 96% of job scams." → ✅ "It scores 96.4% on a 180-row synthetic benchmark."
- ❌ "It's production ready." → ✅ "It's a working prototype with an honest limitations section."
- ❌ "The AI explains the verdict." → ✅ "The LLM only writes prose; the score comes from the ML and rule engines."
- ❌ "It detects all fake jobs." → ✅ "It catches the documented scam archetypes; novel social engineering can still slip through."

---

## 7. One-screen cheat sheet

```
run:      ./run.sh --no-build        seed: python scripts/seed_demo.py
tests:    python -m pytest -q        ->  59 passed
UI:       http://localhost:8000      API: http://localhost:8000/docs

Scam ad      -> 82  High Risk   ML 0.884  rules 75  [UPFRONT_FEE, NO_INTERVIEW, GMAIL]
Genuine job  -> 10  Low  Risk   ML 0.203  rules  0
KYC hard neg ->  9  Low  Risk   ML 0.175  rules  0   <- no false positive
OTP scam     -> 98  High Risk   ML 0.951  rules 100  5 flags
Money mule   -> 75  High Risk   blended 71.4 -> floor 75

Score  = 0.5*ML + 0.5*rules, then floors: CRITICAL>=75, HIGH>=45, 2xMEDIUM>=45
Model  = TF-IDF (1,2)-grams + LogisticRegression, class_weight=balanced, sigmoid calibrated
Eval   = GroupShuffleSplit by archetype (row split leaked variants -> fake 100%)
Rules  = 8, each with severity + weight + quoted evidence
Tests  = 59: rules, floors, migration, SSRF, HTTP surface, storage resilience
```
