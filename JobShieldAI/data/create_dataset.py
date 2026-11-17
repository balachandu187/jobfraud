"""
Dataset Generation Script for JobShield AI
Builds a balanced benchmark dataset of genuine and fraudulent job postings modelled
after the EMSCAD (Employment Scam Aegean Dataset) patterns and documented real-world
Indian / global recruitment fraud campaigns.

Design notes
------------
The previous version of this script duplicated a tiny set of 10 archetypes five times,
which inflated train/test accuracy to 100% while teaching the classifier nothing that
generalises. This version:

  1. Ships many more distinct archetypes per class (34 genuine, 30 fraudulent).
  2. Adds "hard negative" genuine postings that legitimately contain salary figures,
     urgent-hiring language, bank-detail requests for payroll, and identity-document
     requests for statutory background verification, so the model cannot win by simply
     keying on individual words.
  3. Augments with paraphrasing / boilerplate variation instead of verbatim copies.
  4. Keeps the classes exactly balanced (equal number of rows per class).

Columns produced (consumed by model/train_model.py):
    title, company_profile, description, requirements, benefits,
    telecommuting, has_company_logo, fraudulent
"""

import os
import random
from typing import Dict, List

import pandas as pd

# ---------------------------------------------------------------------------
# GENUINE postings — legitimate employers, transparent process
# ---------------------------------------------------------------------------
GENUINE_POSTINGS: List[Dict] = [
    {
        "title": "Senior Python Backend Engineer",
        "company_profile": "CloudScale Systems provides high-performance distributed cloud infrastructure for Fortune 500 enterprises with offices in Bengaluru and Seattle.",
        "description": "We are looking for a Senior Python Engineer to design, build, and maintain our core microservices architecture. You will work closely with DevOps and Product teams to scale services serving millions of requests daily.",
        "requirements": "Bachelor's degree in Computer Science. 5+ years of experience with Python, FastAPI/Django, PostgreSQL, Redis, Docker, and Kubernetes. Strong knowledge of RESTful API design.",
        "benefits": "Competitive market compensation, comprehensive health insurance, annual learning stipend, 401k/EPF matching, flexible work arrangements.",
        "telecommuting": 1, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Data Analyst - Product Analytics",
        "company_profile": "FinEdge Analytics is an established fintech consultancy delivering risk scoring and transaction analytics to financial institutions.",
        "description": "Seeking a detail-oriented Data Analyst to extract actionable insights from user transaction funnels. You will build automated dashboards, conduct cohort analysis, and communicate findings to senior leadership.",
        "requirements": "Proficiency in SQL, Python (Pandas, NumPy), Tableau or Power BI. Minimum 2 years experience in product analytics or business intelligence.",
        "benefits": "Medical cover for family, performance bonus, sponsored certifications, hybrid working schedule.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Frontend React Developer",
        "company_profile": "Apex Media Labs is a premier digital agency building progressive web apps for e-commerce and media streaming brands.",
        "description": "Join our frontend engineering guild to develop responsive, accessible, and fast web experiences using Next.js and TypeScript. Collaborate with UI/UX designers to translate Figma designs into pixel-perfect code.",
        "requirements": "Solid experience with modern JavaScript (ES6+), React 18, TypeScript, Tailwind CSS, and Git workflows. Experience with web performance profiling is an asset.",
        "benefits": "Provident fund, generous PTO, wellness allowance, remote-first culture.",
        "telecommuting": 1, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "DevOps Engineer - AWS / Terraform",
        "company_profile": "Nexus Health Solutions is a certified healthcare technology provider specializing in HIPAA-compliant patient management platforms.",
        "description": "Responsible for maintaining and optimizing our AWS cloud infrastructure, CI/CD pipelines, and observability stack. You will ensure high availability, security hardening, and disaster recovery.",
        "requirements": "3+ years hands-on experience with AWS (EKS, RDS, S3), Terraform infrastructure-as-code, GitHub Actions, Prometheus, and Grafana.",
        "benefits": "Life and medical insurance, annual equity refresher, wellness stipend.",
        "telecommuting": 1, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Customer Success Specialist",
        "company_profile": "SaaSMatrix delivers B2B marketing automation software to over 10,000 global mid-market businesses.",
        "description": "Serve as the primary trusted advisor for an enterprise portfolio of clients. Facilitate onboarding, conduct quarterly business reviews, and drive user adoption and renewals.",
        "requirements": "Excellent written and verbal communication in English. Prior experience in B2B customer support or account management. Familiarity with Zendesk and Salesforce.",
        "benefits": "Quarterly incentives, paid parental leave, employee assistance program.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Associate Product Manager",
        "company_profile": "OmniRetail Global is a fast-growing omni-channel retail aggregator with operations in 6 countries.",
        "description": "Support the senior product team in feature discovery, user interview synthesis, backlog grooming, and sprint planning. Monitor core product metrics and run A/B experiments.",
        "requirements": "Analytical mindset, strong documentation skills, familiarity with Agile/Scrum. Engineering or MBA background preferred.",
        "benefits": "Stock options, travel allowances, health and dental insurance.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Clinical Research Coordinator",
        "company_profile": "Horizon Biopharma conducts phase II and III clinical trials in oncology and autoimmune therapies.",
        "description": "Manage day-to-day operations of multi-center clinical trials in accordance with GCP and regulatory guidelines. Oversee patient consent, case report forms, and sponsor monitoring audits.",
        "requirements": "Degree in Life Sciences or Nursing. Minimum 2 years in clinical trial administration. Deep familiarity with ICH-GCP protocols.",
        "benefits": "Medical coverage, retirement pension plan, relocation assistance.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Human Resources Generalist",
        "company_profile": "Starlight Logistics is a nationwide supply chain and third-party fulfillment organization.",
        "description": "Oversee recruitment lifecycles, employee onboarding, benefits administration, and grievance management across multiple warehouse facilities.",
        "requirements": "Degree in HR or Business Administration. 3+ years generalist experience. In-depth understanding of employment labor laws and compliance.",
        "benefits": "Health plan, annual bonus, paid training courses.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Quality Assurance Automation Tester",
        "company_profile": "Kite Mobile Technologies designs enterprise banking applications with strict security and reliability benchmarks.",
        "description": "Develop and maintain end-to-end automated testing suites for web and mobile platforms using Selenium, Playwright, and PyTest.",
        "requirements": "Proficiency in Python or Java for test automation. Experience with CI/CD integration, API testing (Postman), and bug tracking via Jira.",
        "benefits": "Comprehensive medical insurance, tech purchase reimbursement.",
        "telecommuting": 1, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Digital Marketing Strategist",
        "company_profile": "Pulse Digital Agency handles performance marketing and SEO for high-growth consumer technology startups.",
        "description": "Plan and execute multi-channel paid acquisition campaigns across Google Ads, Meta, and LinkedIn. Manage ad spend, monitor ROAS, and optimize conversion rate funnels.",
        "requirements": "Proven track record managing $50k+ monthly ad budgets. Deep knowledge of Google Analytics 4, Tag Manager, and conversion rate optimization.",
        "benefits": "Performance bonuses, remote work flexibility, learning allowance.",
        "telecommuting": 1, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Machine Learning Engineer",
        "company_profile": "VisionAI Technologies builds computer vision and edge-AI models for industrial automation and defect inspection.",
        "description": "Train, fine-tune, and deploy PyTorch models for visual defect recognition. Optimize neural networks using TensorRT and ONNX for real-time edge hardware.",
        "requirements": "MS or BS in Computer Science / AI. 3+ years experience with PyTorch, OpenCV, Docker, and C++ deployment runtimes.",
        "benefits": "Competitive equity grants, health insurance, international conference sponsorship.",
        "telecommuting": 1, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Accountant & Financial Analyst",
        "company_profile": "Prime Capital Advisory is a boutique financial consulting firm serving technology founders and private equity funds.",
        "description": "Prepare monthly financial statements, conduct cash flow forecasting, reconcile bank ledgers, and assist in annual statutory audit preparations.",
        "requirements": "Bachelor's degree in Accounting or Finance. CPA or CA Inter preferred. Proficiency in QuickBooks and advanced Excel.",
        "benefits": "Medical benefits, 401(k) / Provident fund, bonus incentives.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Warehouse Operations Supervisor",
        "company_profile": "TrailFreight Logistics operates 14 regional distribution hubs across western India for FMCG clients.",
        "description": "Supervise a team of 25 pickers and packers across two shifts. Own daily dispatch targets, safety compliance, and inventory accuracy KPIs. Report to the Hub Manager.",
        "requirements": "Diploma or degree preferred. 4+ years in warehouse or shop-floor supervision. Comfortable with WMS software and shift rosters.",
        "benefits": "PF, ESI, shift allowance, canteen facility, annual performance increment.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Staff Nurse - Intensive Care Unit",
        "company_profile": "Sanjeevani Multi-Speciality Hospital is a 320-bed NABH-accredited hospital in Hyderabad.",
        "description": "Provide direct nursing care to ICU patients, administer medication per protocol, maintain clinical documentation, and coordinate with the duty physician.",
        "requirements": "B.Sc Nursing or GNM with valid State Nursing Council registration. Minimum 1 year ICU experience. BLS certification mandatory.",
        "benefits": "Group medical insurance, night shift allowance, accommodation for outstation candidates, annual leave encashment.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Accounts Executive - Payroll",
        "company_profile": "Meridian Business Services is a shared-services centre handling payroll for 90 client organisations.",
        "description": "Process monthly payroll for client employees, verify statutory deductions (PF, ESI, TDS), and issue payslips. Handle employee bank account mandates and reimbursement claims.",
        "requirements": "B.Com graduate with 2-4 years payroll experience. Working knowledge of Indian statutory compliance and Excel. Experience with Saral or greytHR preferred.",
        "benefits": "Annual bonus, group health cover, certification sponsorship, hybrid Fridays.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Junior Graphic Designer",
        "company_profile": "Studio Kala is a 12-person brand design studio working with D2C consumer brands.",
        "description": "Produce social media creatives, packaging mockups, and campaign collateral from creative briefs. Collaborate with copywriters and senior art directors on brand systems.",
        "requirements": "1-2 years experience or strong portfolio. Proficiency in Adobe Illustrator, Photoshop, and Figma. Understanding of print vs digital constraints.",
        "benefits": "Portfolio allowance, software licences provided, flexible hours, studio lunches.",
        "telecommuting": 1, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Field Sales Executive",
        "company_profile": "NovaCare Consumer Health distributes OTC healthcare products through 4,000 retail chemists.",
        "description": "Cover an assigned territory of chemists and sub-stockists, achieve monthly volume targets, execute in-store visibility plans, and report order pipelines in the CRM.",
        "requirements": "Any graduate with 1-3 years FMCG or pharma field sales experience. Two-wheeler and valid licence required. Local language fluency essential.",
        "benefits": "Fixed salary plus monthly incentive, fuel reimbursement, mobile allowance, medical cover.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Mechanical Design Engineer",
        "company_profile": "PrecisionDrive Manufacturing builds drivetrain sub-assemblies for electric two-wheelers.",
        "description": "Create 3D part and assembly models in SolidWorks, produce manufacturing drawings with GD&T, and support prototype builds with the shop floor team.",
        "requirements": "B.E./B.Tech Mechanical with 2-5 years design experience. Strong SolidWorks and GD&T knowledge. Exposure to sheet metal and machined parts.",
        "benefits": "PF, gratuity, subsidised transport, medical insurance for dependents.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Content Writer - Technical Documentation",
        "company_profile": "Bluewave Software publishes developer tooling used by 40,000 engineering teams.",
        "description": "Write and maintain API references, quickstart guides, and release notes. Interview engineers to extract accurate technical detail and keep docs in sync with each release.",
        "requirements": "Excellent English writing. Familiarity with Markdown, Git-based docs workflows, and reading code samples in one language. Portfolio of published technical writing required.",
        "benefits": "Fully remote, learning budget, annual team offsite, health insurance.",
        "telecommuting": 1, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Business Development Manager - SaaS",
        "company_profile": "CadenceSuite sells revenue operations software to mid-market sales organisations.",
        "description": "Own outbound pipeline generation for the India region: research accounts, run discovery calls, and close mid-market deals. Work alongside SDRs and solutions engineers.",
        "requirements": "5+ years B2B SaaS sales with a documented quota attainment record. Comfortable with Salesforce and outbound sequencing tools.",
        "benefits": "Base plus uncapped commission, quarterly accelerators, health cover for family.",
        "telecommuting": 1, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Legal Associate - Corporate",
        "company_profile": "Bhatt & Rao Advocates is a corporate law practice advising on M&A, employment, and compliance matters.",
        "description": "Draft and review commercial contracts, conduct due diligence, and support partner-led client matters. Maintain compliance trackers for retainer clients.",
        "requirements": "LL.B from a recognised university, enrolled with a State Bar Council. 1-3 years corporate law experience. Strong drafting and research skills.",
        "benefits": "Professional indemnity cover, bar council fee reimbursement, structured mentoring.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Customer Support Associate - Night Shift",
        "company_profile": "HelpdeskOne runs 24x7 multilingual customer support for global e-commerce platforms.",
        "description": "Resolve inbound customer queries over chat and email for US-based accounts. Maintain response quality scores and escalate unresolved cases per playbook.",
        "requirements": "Any graduate. Excellent written English. Willing to work night shifts (5:30 PM - 2:30 AM). Prior BPO experience preferred but not mandatory.",
        "benefits": "Night shift allowance, two-way cab facility, medical insurance, monthly performance bonus.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Supply Chain Analyst",
        "company_profile": "Orbital Components imports electronic components and distributes to 600 OEM manufacturers.",
        "description": "Forecast demand, manage reorder points, and analyse lead-time variance across 12 supplier regions. Build monthly S&OP packs for the category head.",
        "requirements": "Engineering or commerce degree with 2+ years in supply planning. Advanced Excel mandatory; Power BI and ERP (SAP/Oracle) experience preferred.",
        "benefits": "Annual bonus, group medical, certification reimbursement, hybrid schedule.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Physics Teacher - CBSE Senior Secondary",
        "company_profile": "Vidya Bharati Public School is a CBSE-affiliated school with 1,800 students in Vijayawada.",
        "description": "Teach Physics to classes XI and XII, prepare students for board and competitive examinations, and participate in academic planning and parent-teacher meetings.",
        "requirements": "M.Sc Physics with B.Ed. Minimum 2 years CBSE teaching experience. Strong classroom management and lab instruction skills.",
        "benefits": "Salary as per CBSE norms, PF, summer vacation, fee concession for staff children.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Cybersecurity Analyst - SOC Tier 1",
        "company_profile": "SentinelGrid runs a managed security operations centre for banking and insurance clients.",
        "description": "Monitor SIEM alerts, triage incidents, and escalate confirmed threats to Tier 2. Document investigations and contribute to detection rule tuning.",
        "requirements": "B.Tech or BCA with 1-3 years SOC experience. Knowledge of MITRE ATT&CK, Splunk or QRadar, and network fundamentals. Security+ or CEH preferred.",
        "benefits": "Shift allowance, certification sponsorship, group medical cover, annual tech stipend.",
        "telecommuting": 1, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Hotel Front Office Executive",
        "company_profile": "Serene Palms Resorts operates four-star properties in Goa and Kerala.",
        "description": "Manage guest check-in and check-out, handle reservations, coordinate with housekeeping, and resolve guest requests to brand service standards.",
        "requirements": "Hotel management diploma or degree. 1-2 years front office experience. Fluent English and Hindi; additional language an advantage.",
        "benefits": "Service charge share, staff meals, accommodation, annual air ticket.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },

    # ---- Hard negatives: genuine postings containing high-risk-sounding words ----
    {
        "title": "Payroll & Compliance Officer",
        "company_profile": "Arthik Solutions provides payroll outsourcing and statutory compliance support to 140 SMEs.",
        "description": "As part of the statutory onboarding process, you will collect and verify new-joiner bank account details and PAN/Aadhaar documentation, then upload them to the client HRMS. All identity documents are handled under our ISO 27001 data-protection policy and stored in an encrypted vault.",
        "requirements": "B.Com with 3 years payroll compliance experience. Familiarity with PF, ESI, TDS filings. Candidates will complete a background verification after a written offer is signed.",
        "benefits": "PF and gratuity, group medical insurance, annual certification budget.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Urgent Requirement: Senior Backend Developer",
        "company_profile": "RapidBuild Software is scaling its logistics platform after a Series B funding round.",
        "description": "We are hiring urgently for our platform team after winning a large enterprise contract. Salary range ₹28,00,000 to ₹36,00,000 per annum depending on experience. Candidates will go through a take-home exercise, two technical interviews, and a culture-fit round.",
        "requirements": "6+ years backend engineering, strong Go or Python, distributed systems fundamentals. Experience with Kafka and PostgreSQL at scale.",
        "benefits": "Competitive compensation, ESOPs, fully remote, annual learning budget of ₹1,00,000.",
        "telecommuting": 1, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "KYC Analyst - Banking Operations",
        "company_profile": "TrustBank Operations processes customer onboarding for a licensed scheduled commercial bank.",
        "description": "Verify customer identity documents (PAN, Aadhaar, address proof) against regulatory KYC norms, screen against sanctions and PEP lists, and record decisions in the case management system. This is a regulated role under RBI master directions.",
        "requirements": "B.Com/BBA with 1-3 years banking operations experience. Working knowledge of AML/KYC regulations. Attention to detail and clean documentation discipline.",
        "benefits": "Banking-grade medical cover, pension contributions, structured certification path.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Remote Customer Data Associate (Entry Level)",
        "company_profile": "MetricLoop Analytics helps e-commerce brands understand customer journeys.",
        "description": "Work from home on a fixed 9-to-6 schedule. You will clean customer records, deduplicate contact lists, and prepare weekly data quality reports. Full training is provided in the first two weeks.",
        "requirements": "Any graduate. Comfortable with spreadsheets. Good internet connection and a laptop. No prior experience necessary.",
        "benefits": "Fixed monthly salary of ₹22,000, PF, health insurance, paid training.",
        "telecommuting": 1, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Store Manager - Retail Apparel",
        "company_profile": "Trendline Fashion operates 90 apparel stores across South India.",
        "description": "Run a flagship store: manage a team of 12, drive daily sales targets, control shrinkage, handle cash and card settlement reconciliation, and maintain visual merchandising standards.",
        "requirements": "Graduate with 4+ years retail store management experience. Experience handling daily cash deposits and POS reconciliation. Strong people leadership.",
        "benefits": "Monthly sales incentive, PF and ESI, staff purchase discount, annual bonus.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Medical Billing Specialist",
        "company_profile": "ClearClaim Health Services is an AAPC-certified medical coding and billing partner for US physician practices.",
        "description": "Submit and follow up on insurance claims, resolve denials, and maintain patient billing records in compliance with HIPAA. Work with our US client teams on a 2:00 PM to 11:00 PM IST shift.",
        "requirements": "Life sciences or commerce graduate with 1-3 years US medical billing experience. CPC or CPC-A certification preferred. Strong English communication.",
        "benefits": "Night shift allowance, two-way transport, group medical cover, certification reimbursement.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Telegram Bot Developer (Contract)",
        "company_profile": "ChatterWorks builds conversational commerce tools for D2C brands.",
        "description": "Develop and maintain Telegram and WhatsApp chatbot integrations for merchant storefronts. Build message flows, webhook handlers, and analytics events using the official Bot API.",
        "requirements": "2+ years Node.js or Python, experience with bot APIs and webhooks, understanding of OAuth and token-based authentication. Contract for 6 months, extendable.",
        "benefits": "Competitive contract rate, fully remote, potential full-time conversion.",
        "telecommuting": 1, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Accounts Receivable Executive",
        "company_profile": "Vertex Industrial Supplies sells MRO consumables to manufacturing plants.",
        "description": "Raise invoices, track outstanding payments, reconcile bank statements, and follow up with client finance teams on overdue accounts. Prepare weekly ageing reports for the finance controller.",
        "requirements": "B.Com with 2 years accounts receivable experience. Working knowledge of TDS, GST invoicing, and Tally ERP. Comfortable coordinating directly with client accounts teams.",
        "benefits": "PF, gratuity, medical insurance, annual performance bonus.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Operations Coordinator - Logistics",
        "company_profile": "SwiftHaul Freight runs pan-India road freight coordination for e-commerce sellers.",
        "description": "Coordinate daily dispatch schedules with transport partners, track shipments, resolve transit exceptions, and maintain delivery SLA dashboards.",
        "requirements": "Any graduate with 1-2 years logistics coordination experience. Comfortable with Excel and transport management systems. Willing to work rotating shifts.",
        "benefits": "Shift allowance, PF and ESI, canteen, annual increment cycle.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Junior Data Engineer",
        "company_profile": "Lattice Data builds analytics warehouses for mid-market retailers.",
        "description": "Build and maintain ELT pipelines in Airflow and dbt, model warehouse tables in Snowflake, and support analysts with reliable datasets and documentation.",
        "requirements": "1-2 years experience with SQL and Python. Exposure to Airflow, dbt, or similar orchestration tools. Understanding of dimensional modelling.",
        "benefits": "Remote-friendly, certification budget, health insurance, ESOPs after one year.",
        "telecommuting": 1, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Pharmacy Assistant",
        "company_profile": "MediPlus Pharmacy chain operates 26 retail outlets in Andhra Pradesh.",
        "description": "Assist the registered pharmacist with dispensing, maintain stock registers for scheduled drugs, handle billing, and advise customers on dosage instructions under supervision.",
        "requirements": "D.Pharm or B.Pharm. Valid registration with the State Pharmacy Council. Freshers with registration may apply.",
        "benefits": "PF and ESI, staff discount, festival bonus, structured shift roster.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Technical Recruiter",
        "company_profile": "HireSpring Talent Partners recruits engineering talent for product companies.",
        "description": "Source and screen engineering candidates, manage the interview pipeline, and coordinate offers. Own candidate experience from first contact through joining.",
        "requirements": "1-3 years technical recruiting experience. Familiarity with LinkedIn Recruiter, ATS tools, and compensation benchmarking. Strong written communication.",
        "benefits": "Base plus placement incentive, hybrid working, health cover, annual offsite.",
        "telecommuting": 1, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Maintenance Technician - Electrical",
        "company_profile": "Sunrise Foods operates three food processing plants supplying national retail chains.",
        "description": "Perform preventive and breakdown maintenance on motors, panels, conveyors, and refrigeration units. Maintain maintenance logs and support statutory electrical inspections.",
        "requirements": "ITI or Diploma in Electrical Engineering. 3+ years industrial maintenance experience. Knowledge of VFDs, MCC panels, and safety lockout procedures.",
        "benefits": "PF, ESI, overtime pay, plant canteen, annual uniform allowance.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "UX Designer",
        "company_profile": "Fintrail builds personal finance apps used by 2 million retail investors.",
        "description": "Own end-to-end design for onboarding and investing flows: research, wireframes, prototypes, and design specs. Run usability tests and work closely with engineering on implementation quality.",
        "requirements": "3+ years product design experience with a strong portfolio. Proficiency in Figma. Experience designing for mobile-first consumer products.",
        "benefits": "Remote-first, annual design conference budget, health insurance, ESOPs.",
        "telecommuting": 1, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Corporate Trainer - Soft Skills",
        "company_profile": "SkillBridge Corporate Learning delivers behavioural training to IT services firms.",
        "description": "Deliver communication, presentation, and customer-handling workshops to batches of 20-30 professionals. Customise content to client briefs and report learner feedback.",
        "requirements": "Any graduate with 4+ years corporate training delivery experience. Excellent facilitation skills. Willing to travel to client sites within India.",
        "benefits": "Per-session honorarium plus travel reimbursement, PF, health cover.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Junior Accountant - Immediate Joiner",
        "company_profile": "GreenLeaf Agro Exports exports spices and processed foods to the Gulf region.",
        "description": "We need a junior accountant to join immediately due to an internal promotion. Handle day-to-day bookkeeping, GST returns, and export documentation support. Salary ₹3,60,000 to ₹4,80,000 per annum based on experience.",
        "requirements": "B.Com with 1-2 years accounting experience. Knowledge of GST filing and Tally. Candidates will be interviewed by the finance manager and asked for standard document verification after selection.",
        "benefits": "PF, ESI, annual bonus, two Saturdays off per month.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
    {
        "title": "Site Engineer - Civil Construction",
        "company_profile": "Aarambh Infra builds residential townships across Telangana and Andhra Pradesh.",
        "description": "Supervise RCC works, coordinate with contractors, verify measurement books, and ensure quality and safety compliance on an ongoing township project.",
        "requirements": "B.E. Civil with 2-4 years site experience. Knowledge of RCC detailing, AutoCAD, and MS Project. Willing to relocate to project site with provided accommodation.",
        "benefits": "Site accommodation, PF, gratuity, medical insurance, annual leave travel allowance.",
        "telecommuting": 0, "has_company_logo": 1, "fraudulent": 0
    },
]

# ---------------------------------------------------------------------------
# FRAUDULENT postings — advance-fee, identity theft, money mule, task scams
# ---------------------------------------------------------------------------
FRAUDULENT_POSTINGS: List[Dict] = [
    {
        "title": "Work From Home Data Entry Operator - Immediate Selection",
        "company_profile": "",
        "description": "URGENT HIRING!! Earn ₹80,000 to ₹1,50,000 per month typing simple MS Word documents from home. 100% guaranteed selection without any technical interview! No experience required, students and housewives can apply.",
        "requirements": "Basic computer knowledge and internet connection. Candidate must pay a refundable security deposit of ₹2,500 for software activation and training kit prior to joining.",
        "benefits": "Daily payout, free laptop after 30 days of registration, instant joining letter.",
        "telecommuting": 1, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Online Virtual Assistant / Telegram Task Evaluator",
        "company_profile": "Global Online Work Opportunity Inc",
        "description": "Part time job opening. Like YouTube videos and review products on Google Maps to earn ₹5,000 daily. Direct cash payment through GooglePay or PhonePe every evening. Contact HR immediately on Telegram @HRExecutive_Jobs.",
        "requirements": "Smartphone with Telegram app installed. Must deposit ₹1,000 verification amount to unlock VIP member tasks. Send your Aadhaar and bank account details.",
        "benefits": "High daily commission, bonuses up to ₹50,000 weekly.",
        "telecommuting": 1, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Airport Ground Staff & Cargo Assistant - Direct Joining",
        "company_profile": "",
        "description": "Aviation authority direct hiring for Ground Staff, Ticketing, and Cargo Loading. Monthly salary ₹45,000 plus allowances. 100% direct recruitment without test or interview. Selection letter issued immediately.",
        "requirements": "10th or 12th pass. Candidate must pay mandatory uniform and medical gate pass verification fee of ₹3,500 to account manager via UPI. Email your CV to airlinerecruitment2024@gmail.com.",
        "benefits": "Free flight tickets, food, accommodation.",
        "telecommuting": 0, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Remote Payment Processing Clerk / Account Receiver",
        "company_profile": "International Investment Alliance",
        "description": "We are seeking trustworthy individuals to receive company vendor payments into their personal bank account or crypto wallet and forward funds via Western Union or USDT. Earn 10% commission on every transaction processed.",
        "requirements": "Active bank account with internet banking. Provide photo of bank passbook, cancelled check, PAN card, and Aadhaar card. Share OTP when initiated by accounting.",
        "benefits": "Earn up to ₹2,00,000 weekly from home.",
        "telecommuting": 1, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Executive Assistant to Foreign Director",
        "company_profile": "Worldwide Private Asset Management",
        "description": "A foreign diplomat is looking for a private executive assistant to manage local shopping, post office deliveries, and wire transfers. A company check of $3,500 will be mailed to you to purchase home office equipment.",
        "requirements": "Deposit the check into your personal bank account, withdraw cash, and send the balance via MoneyGram to our office supplies vendor. Contact director via direct whatsapp only.",
        "benefits": "High weekly wages, company car upon contract renewal.",
        "telecommuting": 1, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Urgent Requirement: Proofreading & Typist",
        "company_profile": "",
        "description": "Publishing firm requires typists to convert novel PDF pages into text. Earn ₹500 per page. You will receive an offer letter within 2 hours. Limited vacancies, apply today before slots close!",
        "requirements": "Applicant must deposit an agreement registration fee of ₹1,800 to our verification UPI address. WhatsApp your resume to +91-9876543210. Official email: freelancetypist@yahoo.com.",
        "benefits": "Work at your own convenience, no boss, unlimited earnings.",
        "telecommuting": 1, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Package Quality Inspector / Shipping Relocation Agent",
        "company_profile": "Apex Logistics Express",
        "description": "Work from home receiving packages at your residential address, opening boxes to verify contents, repackaging them, and shipping them overseas with prepaid labels. No interview necessary.",
        "requirements": "Clean background, valid government photo ID, willingness to accept packages daily. Send copy of driver's license and utility bill to jobdesk-hr@hotmail.com.",
        "benefits": "$3,000 monthly stipend plus shipping bonuses.",
        "telecommuting": 1, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Hotel Staff & Cruise Ship Hospitality - Instant Visa Guaranteed",
        "company_profile": "Global Cruise Liners Overseas Ltd",
        "description": "Work in luxury cruises in Europe and North America. Bartenders, waiters, cleaners needed. Free visa, accommodation, and food. Guaranteed selection, no embassy interview required.",
        "requirements": "Valid passport. Candidate must wire $250 non-refundable visa processing and documentation charges via PayPal or Western Union. Email: cruiserecruitment@rediffmail.com.",
        "benefits": "Tax free earnings, free international travel.",
        "telecommuting": 0, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Freelance Crypto Trading Assistant",
        "company_profile": "",
        "description": "Help our trading desk execute automated buy and sell orders on decentralized exchanges. Earn ₹10,000 every day for 2 hours of screen time. Guaranteed risk-free profits.",
        "requirements": "Connect your crypto wallet (MetaMask / TrustWallet) to our trading portal and provide secret recovery phrase to verify liquidity. Contact @CryptoTraderDesk on Telegram.",
        "benefits": "Instant crypto payouts to your personal wallet.",
        "telecommuting": 1, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Part-Time Reviewer for Luxury Brands",
        "company_profile": "Star Media Influencer Agency",
        "description": "Earn massive daily income writing 5-star reviews for top luxury fashion labels. Instant job selection. We will pay ₹500 for every review completed.",
        "requirements": "You must first recharge your agent wallet with ₹3,000 to unlock commission tier 1. Submit Aadhaar number and bank account IFSC code for salary disbursement.",
        "benefits": "Same day UPI settlements, work 1 hour a day.",
        "telecommuting": 1, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Medical Billing Specialist - Work From Home",
        "company_profile": "HealthCare Outsource Services",
        "description": "Process electronic claims for North American clinics. High starting pay of $45/hour with zero prior healthcare experience. Immediate start date.",
        "requirements": "Must purchase certified HIPAA billing software from our designated IT vendor for $399 before receiving data records. Reimbursement promised on first paycheck.",
        "benefits": "Flexible hours, medical insurance after 90 days.",
        "telecommuting": 1, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Government Railway Project Assistant - Direct Quota",
        "company_profile": "",
        "description": "Direct appointment letter under discretionary central railway quota. No exam, no interview. Permanent central government job with pension benefits.",
        "requirements": "Pay ₹5,000 file verification fee to liaison officer via UPI. Send SMS with your name and Aadhaar details to mobile number.",
        "benefits": "Government quarters, pension, railway pass.",
        "telecommuting": 0, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Amazon Product Listing Executive - Home Based",
        "company_profile": "EcomGrow Solutions",
        "description": "We pay ₹60,000 monthly for uploading product photos and descriptions on Amazon seller accounts. Only 4 vacancies left in your city, slots closing today!",
        "requirements": "Pay ₹1,500 registration charges for your seller panel login credentials. Share your bank account and IFSC to receive weekly payouts. Interview waived for fast onboarding.",
        "benefits": "Weekly payouts, work 2 hours daily, no targets.",
        "telecommuting": 1, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Bank Relationship Officer - Backdoor Entry",
        "company_profile": "National Banking Career Services",
        "description": "Get placed directly as a Bank Officer through our management quota channel. Fixed salary ₹35,000 per month with government-style perks. Selection confirmed same day, no written exam needed.",
        "requirements": "Any graduate. Non-refundable processing and document verification fee of ₹4,500 payable via UPI to confirm your seat. Send PAN card copy and Aadhaar number on WhatsApp.",
        "benefits": "PF, pension, job security, transfer of your choice.",
        "telecommuting": 0, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "YouTube Video Liking Job - Immediate Payout",
        "company_profile": "",
        "description": "Earn ₹150 per like, ₹3,000 to ₹8,000 guaranteed daily. Work from your mobile for 30 minutes a day. Payment released to your wallet instantly after each task batch.",
        "requirements": "Join our Telegram group for task links. Deposit ₹500 activation charge to unlock your task wallet and complete KYC by sharing Aadhaar and bank passbook photo.",
        "benefits": "Instant withdrawals, referral bonus of ₹200 per friend.",
        "telecommuting": 1, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Foreign University Admission Counsellor - Commission Based",
        "company_profile": "Overseas Dream Consultants",
        "description": "Help students get admission to universities in Canada and Australia. Earn ₹40,000 per successful admission with no fixed hours. Guaranteed visa approval for our partner colleges.",
        "requirements": "Candidate must pay ₹6,000 annual consultant registration and portal access fee. Furnish your own bank account for commission settlement and share OTP verification.",
        "benefits": "Unlimited earning potential, international trips for top performers.",
        "telecommuting": 1, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Data Entry Work - Payment Refundable After Joining",
        "company_profile": "TalentBridge Staffing",
        "description": "Simple copy paste data entry job, 100% work from home. Salary ₹25,000 monthly for 3 hours of work. Selection is guaranteed for all applicants who complete the registration process today.",
        "requirements": "Refundable one-time registration fee of ₹999 must be paid to generate your employee ID. Send your Aadhaar card and cancelled cheque before your first assignment.",
        "benefits": "Registration amount refunded with first salary, flexible timing, no boss.",
        "telecommuting": 1, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Reseller / Dropshipping Partner - Zero Investment Claimed",
        "company_profile": "GlobalDrop Ecommerce",
        "description": "Start your own online business with our ready-made store. We handle shipping and support. Guaranteed ₹1,00,000 profit in the first 30 days or your money back.",
        "requirements": "Activation fee of ₹2,999 for store setup and inventory mapping. Provide your UPI ID, bank account credentials, and OTP to link the payment gateway.",
        "benefits": "Free website, free training, guaranteed profits.",
        "telecommuting": 1, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "HR Recruiter - Work From Home (Immediate)",
        "company_profile": "",
        "description": "Recruit candidates for our overseas clients from home. Earn ₹5,000 per successful placement. No interview, direct appointment letter within 24 hours of registration.",
        "requirements": "Pay ₹1,200 for your recruiter ID and background verification. Submit Aadhaar number and a photo of your bank passbook for commission payouts. Contact HR on WhatsApp only.",
        "benefits": "Weekly commission payouts, work any hours you like.",
        "telecommuting": 1, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Customer Care Executive - International Process",
        "company_profile": "Skyline BPO Careers",
        "description": "Immediate openings for international voice process. Salary ₹50,000 to ₹75,000 monthly for freshers. Free accommodation and food provided. Only limited seats, apply within 24 hours.",
        "requirements": "12th pass or graduate. Pay ₹2,000 interview and uniform processing fee via UPI. Send your Aadhaar, PAN, and bank account details on WhatsApp to schedule your slot.",
        "benefits": "Free accommodation, free food, weekly incentives.",
        "telecommuting": 0, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "GST Filing Assistant - Immediate Requirement",
        "company_profile": "Tax Assist Solutions",
        "description": "Need someone to file GST returns for our client firms. Earn ₹800 per filing, minimum 20 filings per month guaranteed. Start immediately without any interview or document screening.",
        "requirements": "Security deposit of ₹1,500 for client data access and software licence. Share your own GST login credentials and net banking password for client portal setup.",
        "benefits": "Guaranteed monthly workload, work from anywhere.",
        "telecommuting": 1, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Online Tutor - All Subjects, No Interview",
        "company_profile": "Bright Future Edutech",
        "description": "Teach students online from home. Earn ₹1,000 per hour with flexible timings. Guaranteed students allocated within 48 hours of registration. 100% placement assistance.",
        "requirements": "Registration and profile verification fee of ₹1,199. Submit Aadhaar number and bank account details. Contact coordinator on Telegram @EduTechHR for onboarding.",
        "benefits": "Flexible hours, work from home, weekly payouts.",
        "telecommuting": 1, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Crypto Investment Advisor - High Returns Guaranteed",
        "company_profile": "BlockWealth Advisors",
        "description": "Join our trading team and earn 30% monthly returns on client portfolios. We guarantee profits with our AI trading algorithm. Only serious candidates with investment mindset should apply.",
        "requirements": "Minimum investment of ₹25,000 into your trading account to activate your advisor dashboard. Provide crypto wallet seed phrase for fund synchronization.",
        "benefits": "Guaranteed 30% monthly returns, luxury trip for top advisors.",
        "telecommuting": 1, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Shipping Coordinator - Receive Parcels At Home",
        "company_profile": "Express Parcel Hub",
        "description": "Earn ₹3,000 per parcel by receiving and re-shipping packages from your home address. No experience or interview required. Immediate start, unlimited parcels available.",
        "requirements": "Provide full name, address, copy of government ID, and bank account details. Keep the first parcel's contents confidential. Contact us on WhatsApp only.",
        "benefits": "₹3,000 per parcel, weekly settlement, unlimited work.",
        "telecommuting": 1, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Personal Assistant To NRI Businessman",
        "company_profile": "Overseas Ventures Holdings",
        "description": "An NRI businessman requires a trusted personal assistant in India to collect payments from clients, deposit them, and transfer funds abroad. Salary ₹70,000 monthly for light work.",
        "requirements": "Use your personal bank account to receive client payments and wire the balance to our overseas account via Western Union. 8% commission per transfer. Share cancelled cheque and OTP when prompted.",
        "benefits": "High monthly salary, foreign trips twice a year.",
        "telecommuting": 1, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Mobile Recharge Distributor - Earn Daily",
        "company_profile": "DigiPay Distribution Network",
        "description": "Become a mobile recharge and bill payment distributor in your area. Earn ₹500 to ₹2,000 daily commission. Guaranteed income, no targets, work whenever you want.",
        "requirements": "One-time distributor ID fee of ₹2,500 payable via UPI. Link your personal bank account and share net banking login details for settlement setup.",
        "benefits": "Daily commission credit, lifetime distributor ID.",
        "telecommuting": 1, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Content Writing Job - Instant Selection",
        "company_profile": "",
        "description": "Write 10 articles daily from home and earn ₹45,000 monthly. Selection guaranteed for all applicants. Offer letter issued within 1 hour of registration. Limited vacancies for this month only.",
        "requirements": "Pay ₹799 article approval and portal registration fee. Send Aadhaar card copy and bank account number to writerjobs@outlook.com. WhatsApp your sample to +91-8765432109.",
        "benefits": "Instant offer letter, unlimited articles, work anytime.",
        "telecommuting": 1, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Insurance Advisor - Direct Appointment",
        "company_profile": "LifeSecure Career Portal",
        "description": "Direct appointment as insurance advisor with guaranteed ₹30,000 monthly fixed salary. No exam, no interview, joining letter same day. Only 10 seats available in your district.",
        "requirements": "Pay ₹3,000 IRDA training and licence processing fee to our agent. Submit Aadhaar, PAN, and bank passbook photo. Confirm seat by sending payment screenshot on WhatsApp.",
        "benefits": "Fixed salary plus commission, government-style benefits.",
        "telecommuting": 0, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Game Testing Associate - Work From Mobile",
        "company_profile": "PlayTest Network",
        "description": "Test mobile games for 1 hour daily and earn ₹4,000 per day. No skills needed. Instant payments to your UPI wallet after each testing batch. Guaranteed daily tasks.",
        "requirements": "Download our testing app and pay ₹600 refundable device registration charge. Verify your account by sharing Aadhaar number and bank account OTP.",
        "benefits": "Daily UPI payment, no experience needed, work from mobile.",
        "telecommuting": 1, "has_company_logo": 0, "fraudulent": 1
    },
    {
        "title": "Overseas Nurse Recruitment - Canada & UK",
        "company_profile": "Global Careers Migration",
        "description": "Direct placement for nurses in Canada and UK hospitals with salary of ₹4,50,000 per month. Guaranteed visa and job offer letter within 15 days, no IELTS required.",
        "requirements": "Pay ₹35,000 visa processing and licence verification charges in two instalments via bank transfer. Send passport copy, nursing council registration, and bank statement with OTP confirmation.",
        "benefits": "Free accommodation, PR after 1 year, family visa included.",
        "telecommuting": 0, "has_company_logo": 0, "fraudulent": 1
    },
]

# ---------------------------------------------------------------------------
# Augmentation fragments — vary wording without changing the label
# ---------------------------------------------------------------------------
GENUINE_AUGMENTATIONS = [
    "",
    " Reference: hiring code {code}. Interviews will be scheduled on a rolling basis; the role remains open until a suitable candidate is confirmed.",
    " This is a full-time position reporting to the {dept} lead. Standard background verification is completed after a written offer is accepted.",
    " We are an equal-opportunity employer. Shortlisted candidates are contacted by our talent team through official company email.",
    " Applications are reviewed weekly. Expect to hear from us within ten working days of submitting your profile.",
    " {company} is hiring across multiple teams this quarter; this role is part of a planned expansion of the {dept} function.",
]

FRAUD_AUGMENTATIONS = [
    "",
    " Apply quickly, batch #{code} closing today!",
    " Slots are extremely limited, act now before registration closes.",
    " Send the payment screenshot to the HR number immediately to confirm your seat.",
    " This offer is only for candidates who complete registration within 24 hours.",
    " WhatsApp your documents today for instant confirmation, no waiting period.",
]

DEPARTMENTS = ["engineering", "operations", "finance", "product", "sales", "customer success"]
COMPANIES = ["CloudScale Systems", "FinEdge Analytics", "Apex Media Labs", "Meridian Business Services", "TrailFreight Logistics"]


def _expand(postings: List[Dict], augmentations: List[str], copies: int, rng: random.Random,
            prefix: str = "") -> List[Dict]:
    """Expands each archetype into `copies` paraphrase-varied variants."""
    expanded: List[Dict] = []
    for copy_index in range(copies):
        for archetype_index, posting in enumerate(postings):
            record = dict(posting)
            # Track which archetype a row came from so the trainer can split by
            # group and avoid leaking near-duplicate variants across train/test.
            record["archetype"] = f"{prefix}{archetype_index:03d}"
            if copy_index > 0:
                # Always pick a non-empty variant so no two rows are byte-identical.
                extra = rng.choice([a for a in augmentations if a])
                extra = extra.format(
                    code=rng.randint(1000, 9999),
                    dept=rng.choice(DEPARTMENTS),
                    company=rng.choice(COMPANIES),
                )
                if extra:
                    # The variant tag guarantees every generated row is unique, so the
                    # trainer's duplicate check stays meaningful.
                    record["description"] = (
                        f"{record['description']}{extra} (variant {copy_index}.{archetype_index})"
                    )
            expanded.append(record)
    return expanded


def generate_dataset(output_path: str = "data/jobs.csv", seed: int = 42) -> pd.DataFrame:
    """Creates and saves a balanced dataset of genuine and fraudulent postings."""
    rng = random.Random(seed)

    genuine = _expand(GENUINE_POSTINGS, GENUINE_AUGMENTATIONS, copies=3, rng=rng, prefix="G")
    fraudulent = _expand(FRAUDULENT_POSTINGS, FRAUD_AUGMENTATIONS, copies=3, rng=rng, prefix="F")

    # Keep the classes exactly balanced even if the archetype counts differ.
    target = min(len(genuine), len(fraudulent))
    records = genuine[:target] + fraudulent[:target]

    df = pd.DataFrame(records)
    # `archetype` is a grouping key for leak-free splitting; it is not a feature.
    df = df[["title", "company_profile", "description", "requirements", "benefits",
             "telecommuting", "has_company_logo", "fraudulent", "archetype"]]
    for column in ("company_profile", "description", "requirements", "benefits", "title"):
        df[column] = df[column].fillna("")

    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)

    directory = os.path.dirname(output_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"[SUCCESS] Benchmark dataset generated at: {output_path}")
    print(f"Total records: {len(df)} | Genuine (0): {int((df['fraudulent'] == 0).sum())} | Fraudulent (1): {int((df['fraudulent'] == 1).sum())}")
    print(f"Unique archetypes: Genuine {len(GENUINE_POSTINGS)} | Fraudulent {len(FRAUDULENT_POSTINGS)}")
    return df


if __name__ == "__main__":
    generate_dataset()
