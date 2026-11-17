"""
JobShield AI — AI-Powered Fake Job and Recruitment Scam Detection System
Streamlit Main Application
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json

# Local modules — the Streamlit UI calls the same service layer as the REST API so
# the ML/rules/risk logic can never diverge between the two front ends.
from services import DetectionService, InputError, ScanPayload
from utils.ollama_client import OllamaClient

# Page Configuration
st.set_page_config(
    page_title="JobShield AI — Fake Job Scam Detection",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Professional Navy & Slate Theme)
st.markdown("""
<style>
    /* Global Styling */
    .main {
        background-color: #0F172A;
    }
    .stApp {
        background: linear-gradient(180deg, #0B0F19 0%, #111827 100%);
        color: #F8FAFC;
    }
    
    /* Metric Cards */
    .metric-card {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        text-align: center;
    }
    .metric-title {
        color: #94A3B8;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        color: #F8FAFC;
        font-size: 2rem;
        font-weight: 700;
        margin-top: 6px;
    }

    /* Risk Badges */
    .badge-low {
        background-color: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border: 1px solid #059669;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
    }
    .badge-med {
        background-color: rgba(245, 158, 11, 0.15);
        color: #FBBF24;
        border: 1px solid #D97706;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
    }
    .badge-high {
        background-color: rgba(239, 68, 68, 0.15);
        color: #F87171;
        border: 1px solid #DC2626;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
    }

    /* Warning Alert Box */
    .warning-box {
        background: #1E293B;
        border-left: 5px solid #EF4444;
        padding: 14px 18px;
        border-radius: 6px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize singletons in session state
if "service" not in st.session_state:
    st.session_state.service = DetectionService()

if "ollama" not in st.session_state:
    st.session_state.ollama = OllamaClient()

if "current_scan" not in st.session_state:
    st.session_state.current_scan = None


# Sidebar Navigation
with st.sidebar:
    st.markdown("### 🛡️ **JobShield AI**")
    st.caption("AI-Powered Job Scam Detection System")
    st.markdown("---")
    
    page = st.radio(
        "Navigation",
        ["Home Dashboard", "Scan a Job", "Scan Results", "Scan History", "About the Project"],
        index=0
    )
    
    st.markdown("---")
    st.markdown("#### System Status")
    
    # Model status
    if st.session_state.service.predictor.is_ready:
        st.success("● ML Classifier Ready", icon="✅")
    else:
        st.warning("● Model Not Trained", icon="⚠️")
        
    # Ollama status
    if st.session_state.ollama.is_available():
        st.success("● Ollama AI Online", icon="🤖")
    else:
        st.info("● Ollama Offline (Fallback Active)", icon="ℹ️")
        
    st.caption("v1.0.0 | Local Offline Mode")


# -----------------------------------------------------------------------------
# PAGE 1: HOME DASHBOARD
# -----------------------------------------------------------------------------
if page == "Home Dashboard":
    st.title("🛡️ Recruitment Fraud Prevention Dashboard")
    st.write("Real-time telemetry and aggregated analytics of scanned job advertisements.")
    
    stats = st.session_state.service.statistics()
    
    # Metric cards row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Advertisements</div>
            <div class="metric-value">{stats['total_scans']}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title" style="color: #34D399;">Genuine Postings</div>
            <div class="metric-value" style="color: #34D399;">{stats['low_risk_count']}</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title" style="color: #FBBF24;">Suspicious / Caution</div>
            <div class="metric-value" style="color: #FBBF24;">{stats['medium_risk_count']}</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title" style="color: #F87171;">High-Risk Scams</div>
            <div class="metric-value" style="color: #F87171;">{stats['high_risk_count']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Charts & Telemetry
    col_left, col_right = st.columns([1.2, 1])
    
    with col_left:
        st.subheader("📊 Risk Classification Distribution")
        if stats["total_scans"] > 0:
            fig = px.pie(
                values=[stats['low_risk_count'], stats['medium_risk_count'], stats['high_risk_count']],
                names=['Low Risk (Genuine)', 'Medium Risk (Suspicious)', 'High Risk (Fraudulent)'],
                color=['Low Risk (Genuine)', 'Medium Risk (Suspicious)', 'High Risk (Fraudulent)'],
                color_discrete_map={
                    'Low Risk (Genuine)': '#10B981',
                    'Medium Risk (Suspicious)': '#F59E0B',
                    'High Risk (Fraudulent)': '#EF4444'
                },
                hole=0.45
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#F8FAFC"),
                margin=dict(t=10, b=10, l=10, r=10),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No scan records logged yet. Head over to **'Scan a Job'** to analyze your first advertisement.")

    with col_right:
        st.subheader("⚡ Quick Start Guide")
        st.markdown("""
        **How JobShield AI protects job applicants:**
        1. **Dual-Engine Security:** Runs NLP Machine Learning (TF-IDF + Logistic Regression) alongside a Heuristic Scam Detection Engine.
        2. **Financial Threat Detection:** Detects upfront fee extortion, fake security deposits, and money mule schemes.
        3. **Identity Guard:** Flags unauthorized collection of Aadhaar, bank passbooks, passwords, or OTPs.
        4. **Explainable AI:** Explains *why* an offer is unsafe and prescribes immediate defense recommendations.
        """)
        if st.button("🚀 Start Scanning a Job", use_container_width=True):
            st.session_state["nav_page"] = "Scan a Job"
            st.rerun()

    # Recent scans preview table
    st.markdown("---")
    st.subheader("🕒 Recent Scan Activity")
    recent = st.session_state.service.history(limit=5)
    if recent:
        df_recent = pd.DataFrame(recent)[["timestamp", "job_title", "company_name", "risk_level", "risk_score", "prediction"]]
        df_recent.columns = ["Timestamp", "Job Title", "Company", "Risk Tier", "Risk Score (0-100)", "ML Prediction"]
        st.dataframe(df_recent, use_container_width=True, hide_index=True)
    else:
        st.caption("No recent scan logs found.")


# -----------------------------------------------------------------------------
# PAGE 2: SCAN A JOB
# -----------------------------------------------------------------------------
elif page == "Scan a Job":
    st.title("🔍 Analyze Job Advertisement")
    st.write("Paste an advertisement or use quick benchmark templates to inspect credibility.")

    # Demo Presets for Easy Evaluation
    st.markdown("##### 🧪 Load Example Presets for Fast Testing:")
    pcol1, pcol2, pcol3 = st.columns(3)
    
    preset_choice = None
    if pcol1.button("🚨 Example A: Upfront Fee Scam", use_container_width=True):
        preset_choice = {
            "title": "Work From Home Typist & Data Entry",
            "company": "FastCareers Online Services",
            "salary": "₹80,000 per month",
            "email": "careers.recruitmentdesk@gmail.com",
            "instructions": "Pay ₹2,000 refundable registration fee to confirm your joining. No interview required.",
            "skills": "Basic typing, MS Word, Internet browsing",
            "description": "Congratulations! You are selected for an online work-from-home job with an attractive salary of ₹80,000 per month. Direct selection letter issued without any interview. Pay ₹2,000 registration fees to confirm your position today."
        }
    if pcol2.button("🛡️ Example B: Genuine Tech Role", use_container_width=True):
        preset_choice = {
            "title": "Software Developer (Python / SQL)",
            "company": "ABC Technologies Ltd",
            "salary": "₹12,00,000 - ₹16,00,000 per annum",
            "email": "talent@abctechnologies.com",
            "instructions": "Apply through company's official career portal. Technical interview and coding assessment required.",
            "skills": "Python, SQL, Django/FastAPI, RESTful APIs, Git",
            "description": "Software Developer position at ABC Technologies. Candidates should have solid Python, SQL, and web development skills. Applicants will undergo a technical interview and background check. Apply through the company's official careers portal."
        }
    if pcol3.button("⚠️ Example C: OTP / Identity Scam", use_container_width=True):
        preset_choice = {
            "title": "Back Office Assistant & Payment Coordinator",
            "company": "Apex Global Hires",
            "salary": "₹60,000 monthly",
            "email": "apexhires@yahoo.com",
            "instructions": "Send Aadhaar card, bank account number, and share verification OTP when prompted.",
            "skills": "None required, immediate joining",
            "description": "Immediate hiring! Guaranteed job placement with daily salary. Send your Aadhaar details, bank account information, and OTP to complete registration. Message HR on WhatsApp immediately."
        }

    st.markdown("<br>", unsafe_allow_html=True)

    with st.form("job_scan_form"):
        f1, f2 = st.columns(2)
        with f1:
            job_title = st.text_input("Job Title", value=preset_choice["title"] if preset_choice else "", placeholder="e.g. Senior Software Engineer")
            company_name = st.text_input("Company Name", value=preset_choice["company"] if preset_choice else "", placeholder="e.g. ABC Technologies Ltd")
            salary_info = st.text_input("Offered Salary / Compensation", value=preset_choice["salary"] if preset_choice else "", placeholder="e.g. ₹80,000 per month")
        with f2:
            contact_email = st.text_input("Contact Email / Application Link", value=preset_choice["email"] if preset_choice else "", placeholder="e.g. hr@abctechnologies.com")
            instructions = st.text_input("Application Instructions / Channels", value=preset_choice["instructions"] if preset_choice else "", placeholder="e.g. Apply on careers portal or WhatsApp")
            skills = st.text_input("Required Skills & Qualifications", value=preset_choice["skills"] if preset_choice else "", placeholder="e.g. Python, SQL, REST APIs")

        job_description = st.text_area(
            "Full Job Advertisement Text *",
            value=preset_choice["description"] if preset_choice else "",
            height=180,
            placeholder="Paste the full job posting, email communication, or message text here..."
        )

        submitted = st.form_submit_button("⚡ Analyze Job Credibility", use_container_width=True, type="primary")

    if submitted:
        if not job_description.strip():
            st.error("Please paste the job advertisement text before analyzing.")
        else:
            with st.spinner("Executing ML Inference & Scam Heuristic Rules..."):
                # One shared pipeline: ML -> heuristics -> risk blend -> advice -> SQLite.
                try:
                    result = st.session_state.service.scan(ScanPayload(
                        job_description=job_description,
                        job_title=job_title or "",
                        company_name=company_name or "",
                        salary_info=salary_info or "",
                        contact_email=contact_email or "",
                        instructions=instructions or "",
                        skills=skills or "",
                    )).to_dict()
                except InputError as error:
                    st.error(str(error))
                    result = None

            if result:
                st.session_state.current_scan = result
                st.success("✅ Job advertisement analyzed successfully!")
                st.info("Navigate to **'Scan Results'** tab in the sidebar or view summary below.")
                st.rerun()


# -----------------------------------------------------------------------------
# PAGE 3: SCAN RESULTS
# -----------------------------------------------------------------------------
elif page == "Scan Results":
    st.title("🛡️ Credibility Analysis Results")
    
    scan = st.session_state.current_scan
    if not scan:
        st.warning("No active scan results in memory. Please submit a posting on the **'Scan a Job'** page.")
    else:
        risk = scan["risk_result"]
        ml = scan["ml_result"]
        warnings = risk["warnings"]
        tips = scan["safety_tips"]

        # Header summary banner
        st.markdown(f"""
        <div style="background-color: #1E293B; border-radius: 12px; padding: 24px; border: 1px solid #334155; margin-bottom: 24px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h2 style="margin: 0; color: #F8FAFC;">{scan['job_title'] or 'Job Advertisement'}</h2>
                    <p style="margin: 4px 0 0 0; color: #94A3B8;">Employer: <strong>{scan['company_name'] or 'Not Disclosed'}</strong></p>
                </div>
                <div style="text-align: right;">
                    <span style="font-size: 1.25rem; font-weight: 700; color: {risk['theme_color']};">
                        {risk['risk_level']} ({risk['verdict']})
                    </span>
                    <div style="color: #94A3B8; font-size: 0.85rem; margin-top: 4px;">Security Score: {risk['risk_score']}/100</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Risk Visualizer Columns
        g_col, m_col = st.columns([1, 1])

        with g_col:
            st.subheader("🎯 Composite Risk Meter")
            # Gauge Chart
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=risk["risk_score"],
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Risk Index (0-100)", 'font': {'color': '#F8FAFC', 'size': 18}},
                number={'font': {'color': risk['theme_color'], 'size': 44}},
                gauge={
                    'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "#94A3B8"},
                    'bar': {'color': risk['theme_color']},
                    'bgcolor': "#1E293B",
                    'steps': [
                        {'range': [0, 35], 'color': 'rgba(16, 185, 129, 0.2)'},
                        {'range': [35, 65], 'color': 'rgba(245, 158, 11, 0.2)'},
                        {'range': [65, 100], 'color': 'rgba(239, 68, 68, 0.2)'}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': risk["risk_score"]
                    }
                }
            ))
            fig_gauge.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font={'color': "#F8FAFC"},
                height=260,
                margin=dict(t=30, b=10, l=30, r=30)
            )
            st.plotly_chart(fig_gauge, use_container_width=True)

        with m_col:
            st.subheader("🧠 Dual-Engine Evaluation Breakdown")
            st.markdown(f"""
            - **Machine Learning Classification:** **{ml.get('prediction_label', 'Unknown')}**
            - **ML Fraud Probability:** `{ml.get('fraud_score_pct', 0.0)}%`
            - **ML Genuine Probability:** `{round(ml.get('genuine_probability', 0.0) * 100, 2)}%`
            - **Rule-Based Threat Score:** `{risk['rule_score']} / 100`
            - **Triggered Red Flags:** `{risk['warning_count']} warning signal(s)`
            """)
            st.caption(risk["disclaimer"])

        st.markdown("---")

        # Warnings & Red Flags Section
        st.subheader(f"⚠️ Detected Red Flags ({len(warnings)})")
        if not warnings:
            st.success("No critical scam indicators or high-confidence red flags were detected in this posting.")
        else:
            for w in warnings:
                severity_color = "#EF4444" if w.get("severity") == "CRITICAL" else "#F59E0B"
                st.markdown(f"""
                <div style="background-color: #1E293B; border-left: 5px solid {severity_color}; padding: 16px; border-radius: 6px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <strong style="color: #F8FAFC; font-size: 1.05rem;">{w.get('title')}</strong>
                        <span style="background-color: {severity_color}; color: #FFFFFF; font-size: 0.75rem; font-weight: 700; padding: 2px 8px; border-radius: 4px;">
                            {w.get('severity', 'WARNING')}
                        </span>
                    </div>
                    <p style="color: #CBD5E1; margin: 8px 0 0 0; font-size: 0.95rem;">{w.get('explanation')}</p>
                </div>
                """, unsafe_allow_html=True)

        # Actionable Safety Checklist
        st.markdown("---")
        st.subheader("🛡️ Recommended Safety Actions")
        for tip in tips:
            st.markdown(f"- ✅ **{tip}**")

        # Optional Ollama Local AI Insights
        st.markdown("---")
        st.subheader("🤖 Local AI Synthesis (Optional Ollama Engine)")
        
        col_ollama_ctrl, col_ollama_out = st.columns([1, 2])
        with col_ollama_ctrl:
            st.write("Generate a natural language risk explanation using a locally hosted LLM.")
            ollama_models = st.session_state.ollama.list_models()
            chosen_model = st.selectbox(
                "Select Local Model",
                options=ollama_models if ollama_models else ["llama3.2:latest", "gemma:2b", "mistral"]
            )
            st.session_state.ollama.model_name = chosen_model
            run_ollama = st.button("Generate Local AI Summary", use_container_width=True)

        with col_ollama_out:
            if run_ollama:
                with st.spinner(f"Querying local model '{chosen_model}'..."):
                    ai_res = st.session_state.ollama.generate_explanation(
                        job_title=scan["job_title"],
                        company=scan["company_name"],
                        risk_score=risk["risk_score"],
                        risk_level=risk["risk_level"],
                        warnings=warnings
                    )
                    if ai_res["available"]:
                        st.markdown(f"**Source:** `{ai_res['source']}`")
                        st.write(ai_res["text"])
                    else:
                        st.warning(f"Ollama is unreachable on `localhost:11434`. (Ensure Ollama is started with `ollama run {chosen_model}`)")
                        st.info("System continues to operate fully using deterministic explanation templates.")


# -----------------------------------------------------------------------------
# PAGE 4: SCAN HISTORY
# -----------------------------------------------------------------------------
elif page == "Scan History":
    st.title("📜 Scanned Advertisements Archive")
    st.write("Review, inspect, or manage all historical job credibility audits stored in SQLite.")

    scans = st.session_state.service.history(limit=100)

    if not scans:
        st.info("No scan history logged yet. Analyze job advertisements to populate this archive.")
    else:
        h1, h2 = st.columns([3, 1])
        with h1:
            st.caption(f"Showing **{len(scans)}** most recent analyses.")
        with h2:
            if st.button("🗑️ Clear All Scan Logs", use_container_width=True, type="secondary"):
                st.session_state.service.clear_history()
                st.success("All scan history has been cleared.")
                st.rerun()

        for item in scans:
            with st.expander(f"📌 [{item['timestamp']}] {item['job_title'] or 'Untitled Job'} — {item['company_name'] or 'Unknown Company'} ({item['risk_level']})"):
                ec1, ec2, ec3 = st.columns([1, 1, 1])
                ec1.metric("Risk Score", f"{item['risk_score']}/100")
                ec2.metric("ML Classification", item['prediction'])
                ec3.metric("Red Flags Triggered", item['warning_count'])

                st.markdown("**Original Advertisement Snippet:**")
                st.code(item['job_text'][:300] + ("..." if len(item['job_text']) > 300 else ""), language="text")

                if item["warnings"]:
                    st.markdown("**Logged Warnings:**")
                    for w in item["warnings"]:
                        st.markdown(f"- ⚠️ **{w.get('title')}**: {w.get('explanation')}")

                if st.button(f"Delete Record #{item['id']}", key=f"del_{item['id']}"):
                    st.session_state.service.delete_scan(item['id'])
                    st.success(f"Record #{item['id']} deleted.")
                    st.rerun()


# -----------------------------------------------------------------------------
# PAGE 5: ABOUT THE PROJECT
# -----------------------------------------------------------------------------
elif page == "About the Project":
    st.title("📖 About JobShield AI")
    st.markdown("""
    ### Project Overview
    **JobShield AI** is an intelligent cybersecurity and recruitment scam prevention system. It analyzes job advertisements 
    using a multi-stage hybrid engine combining Natural Language Processing, probabilistic Machine Learning, and 
    heuristic threat detection rules.

    ---
    ### System Architecture & Pipeline
    """)

    st.markdown("""
    ```text
    [ Job Advertisement Text ]
               │
               ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                     HYBRID DETECTION CORE                       │
    │                                                                 │
    │  ┌──────────────────────────────┐ ┌───────────────────────────┐ │
    │  │  Machine Learning Classifier │ │ Rule-Based Threat Engine  │ │
    │  │   - TF-IDF Vectorizer        │ │  - Upfront Fee Regex      │ │
    │  │   - Logistic Regression      │ │  - Identity Theft Regex   │ │
    │  │   - Probabilistic Output     │ │  - Domain Credibility     │ │
    │  └──────────────┬───────────────┘ └─────────────┬─────────────┘ │
    └─────────────────┼───────────────────────────────┼───────────────┘
                      │                               │
                      ▼                               ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                    ENSEMBLE RISK ANALYZER                       │
    │       Weighted Score Blending + Critical Severity Floor         │
    │                Overall Risk Index (0 - 100)                     │
    └─────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                     OUTPUT & PERSISTENCE                        │
    │  - Streamlit Dark UI Dashboard (Plotly Charts)                  │
    │  - SQLite Audit Trail & Analytics                               │
    │  - Optional Local Ollama LLM Advisory                           │
    └─────────────────────────────────────────────────────────────────┘
    ```
    """)

    st.markdown("""
    ---
    ### Technical Specifications
    - **Programming Language:** Python 3.11
    - **Frontend Framework:** Streamlit
    - **NLP & Machine Learning:** Scikit-learn (TF-IDF Vectorizer + Logistic Regression)
    - **Database Engine:** SQLite3 (Local embedded relational store)
    - **Data Visualizations:** Plotly Graph Objects & Express
    - **Local LLM Engine:** Ollama REST API (Fallback to deterministic rules)
    - **Hardware Footprint:** Lightweight (runs locally on 8 GB RAM without cloud fees)
    """)

