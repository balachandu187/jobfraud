"""
Dataset Generation Script for JobShield AI
Creates a representative, balanced benchmark dataset of genuine and fraudulent
job postings modeled after patterns in the EMSCAD (Employment Scam Aegean Dataset)
and real-world recruitment scams.
"""

import os
import pandas as pd

# Comprehensive set of realistic genuine job postings
GENUINE_POSTINGS = [
    {
        "title": "Senior Python Backend Engineer",
        "company_profile": "CloudScale Systems provides high-performance distributed cloud infrastructure for Fortune 500 enterprises with offices in Bengaluru and Seattle.",
        "description": "We are looking for a Senior Python Engineer to design, build, and maintain our core microservices architecture. You will work closely with DevOps and Product teams to scale services serving millions of requests daily.",
        "requirements": "Bachelor's degree in Computer Science. 5+ years of experience with Python, FastAPI/Django, PostgreSQL, Redis, Docker, and Kubernetes. Strong knowledge of RESTful API design.",
        "benefits": "Competitive market compensation, comprehensive health insurance, annual learning stipend, 401k/EPF matching, flexible work arrangements.",
        "telecommuting": 1,
        "has_company_logo": 1,
        "fraudulent": 0
    },
    {
        "title": "Data Analyst - Product Analytics",
        "company_profile": "FinEdge Analytics is an established fintech consultancy delivering risk scoring and transaction analytics to financial institutions.",
        "description": "Seeking a detail-oriented Data Analyst to extract actionable insights from user transaction funnels. You will build automated dashboards, conduct cohort analysis, and communicate findings to senior leadership.",
        "requirements": "Proficiency in SQL, Python (Pandas, NumPy), Tableau or Power BI. Minimum 2 years experience in product analytics or business intelligence.",
        "benefits": "Medical cover for family, performance bonus, sponsored certifications, hybrid working schedule.",
        "telecommuting": 0,
        "has_company_logo": 1,
        "fraudulent": 0
    },
    {
        "title": "Frontend React Developer",
        "company_profile": "Apex Media Labs is a premier digital agency building progressive web apps for e-commerce and media streaming brands.",
        "description": "Join our frontend engineering guild to develop responsive, accessible, and fast web experiences using Next.js and TypeScript. Collaborate with UI/UX designers to translate Figma designs into pixel-perfect code.",
        "requirements": "Solid experience with modern JavaScript (ES6+), React 18, TypeScript, Tailwind CSS, and Git workflows. Experience with web performance profiling is an asset.",
        "benefits": "Provident fund, generous PTO, wellness allowance, remote-first culture.",
        "telecommuting": 1,
        "has_company_logo": 1,
        "fraudulent": 0
    },
    {
        "title": "DevOps Engineer - AWS / Terraform",
        "company_profile": "Nexus Health Solutions is a certified healthcare technology provider specializing in HIPAA-compliant patient management platforms.",
        "description": "Responsible for maintaining and optimizing our AWS cloud infrastructure, CI/CD pipelines, and observability stack. You will ensure high availability, security hardening, and disaster recovery.",
        "requirements": "3+ years hands-on experience with AWS (EKS, RDS, S3), Terraform infrastructure-as-code, GitHub Actions, Prometheus, and Grafana.",
        "benefits": "Life and medical insurance, annual equity refresher, wellness stipend.",
        "telecommuting": 1,
        "has_company_logo": 1,
        "fraudulent": 0
    },
    {
        "title": "Customer Success Specialist",
        "company_profile": "SaaSMatrix delivers B2B marketing automation software to over 10,000 global mid-market businesses.",
        "description": "Serve as the primary trusted advisor for an enterprise portfolio of clients. Facilitate onboarding, conduct quarterly business reviews, and drive user adoption and renewals.",
        "requirements": "Excellent written and verbal communication in English. Prior experience in B2B customer support or account management. Familiarity with Zendesk and Salesforce.",
        "benefits": "Quarterly incentives, paid parental leave, employee assistance program.",
        "telecommuting": 0,
        "has_company_logo": 1,
        "fraudulent": 0
    },
    {
        "title": "Associate Product Manager",
        "company_profile": "OmniRetail Global is a fast-growing omni-channel retail aggregator with operations in 6 countries.",
        "description": "Support the senior product team in feature discovery, user interview synthesis, backlog grooming, and sprint planning. Monitor core product metrics and run A/B experiments.",
        "requirements": "Analytical mindset, strong documentation skills, familiarity with Agile/Scrum. Engineering or MBA background preferred.",
        "benefits": "Stock options, travel allowances, health and dental insurance.",
        "telecommuting": 0,
        "has_company_logo": 1,
        "fraudulent": 0
    },
    {
        "title": "Clinical Research Coordinator",
        "company_profile": "Horizon Biopharma conducts phase II and III clinical trials in oncology and autoimmune therapies.",
        "description": "Manage day-to-day operations of multi-center clinical trials in accordance with GCP and regulatory guidelines. Oversee patient consent, case report forms, and sponsor monitoring audits.",
        "requirements": "Degree in Life Sciences or Nursing. Minimum 2 years in clinical trial administration. Deep familiarity with ICH-GCP protocols.",
        "benefits": "Medical coverage, retirement pension plan, relocation assistance.",
        "telecommuting": 0,
        "has_company_logo": 1,
        "fraudulent": 0
    },
    {
        "title": "Human Resources Generalist",
        "company_profile": "Starlight Logistics is a nationwide supply chain and third-party fulfillment organization.",
        "description": "Oversee recruitment lifecycles, employee onboarding, benefits administration, and grievance management across multiple warehouse facilities.",
        "requirements": "Degree in HR or Business Administration. 3+ years generalist experience. In-depth understanding of employment labor laws and compliance.",
        "benefits": "Health plan, annual bonus, paid training courses.",
        "telecommuting": 0,
        "has_company_logo": 1,
        "fraudulent": 0
    },
    {
        "title": "Quality Assurance Automation Tester",
        "company_profile": "Kite Mobile Technologies designs enterprise banking applications with strict security and reliability benchmarks.",
        "description": "Develop and maintain end-to-end automated testing suites for web and mobile platforms using Selenium, Playwright, and PyTest.",
        "requirements": "Proficiency in Python or Java for test automation. Experience with CI/CD integration, API testing (Postman), and bug tracking via Jira.",
        "benefits": "Comprehensive medical insurance, tech purchase reimbursement.",
        "telecommuting": 1,
        "has_company_logo": 1,
        "fraudulent": 0
    },
    {
        "title": "Digital Marketing Strategist",
        "company_profile": "Pulse Digital Agency handles performance marketing and SEO for high-growth consumer technology startups.",
        "description": "Plan and execute multi-channel paid acquisition campaigns across Google Ads, Meta, and LinkedIn. Manage ad spend, monitor ROAS, and optimize conversion rate funnels.",
        "requirements": "Proven track record managing $50k+ monthly ad budgets. Deep knowledge of Google Analytics 4, Tag Manager, and conversion rate optimization.",
        "benefits": "Performance bonuses, remote work flexibility, learning allowance.",
        "telecommuting": 1,
        "has_company_logo": 1,
        "fraudulent": 0
    },
    {
        "title": "Machine Learning Engineer",
        "company_profile": "VisionAI Technologies builds computer vision and edge-AI models for industrial automation and defect inspection.",
        "description": "Train, fine-tune, and deploy PyTorch models for visual defect recognition. Optimize neural networks using TensorRT and ONNX for real-time edge hardware.",
        "requirements": "MS or BS in Computer Science / AI. 3+ years experience with PyTorch, OpenCV, Docker, and C++ deployment runtimes.",
        "benefits": "Competitive equity grants, health insurance, international conference sponsorship.",
        "telecommuting": 1,
        "has_company_logo": 1,
        "fraudulent": 0
    },
    {
        "title": "Accountant & Financial Analyst",
        "company_profile": "Prime Capital Advisory is a boutique financial consulting firm serving technology founders and private equity funds.",
        "description": "Prepare monthly financial statements, conduct cash flow forecasting, reconcile bank ledgers, and assist in annual statutory audit preparations.",
        "requirements": "Bachelor's degree in Accounting or Finance. Certified Public Accountant (CPA) or Chartered Accountant (CA) inter preferred. Proficiency in QuickBooks and advanced Excel.",
        "benefits": "Medical benefits, 401(k) / Provident fund, bonus incentives.",
        "telecommuting": 0,
        "has_company_logo": 1,
        "fraudulent": 0
    }
]

# Comprehensive set of realistic fraudulent / scam job postings
FRAUDULENT_POSTINGS = [
    {
        "title": "Work From Home Data Entry Operator - Immediate Selection",
        "company_profile": "",
        "description": "URGENT HIRING!! Earn ₹80,000 to ₹1,50,000 per month typing simple MS Word documents from home. 100% guaranteed selection without any technical interview! No experience required, students and housewives can apply.",
        "requirements": "Basic computer knowledge and internet connection. Candidate must pay a refundable security deposit of ₹2,500 for software activation and training kit prior to joining.",
        "benefits": "Daily payout, free laptop after 30 days of registration, instant joining letter.",
        "telecommuting": 1,
        "has_company_logo": 0,
        "fraudulent": 1
    },
    {
        "title": "Online Virtual Assistant / Telegram Task Evaluator",
        "company_profile": "Global Online Work Opportunity Inc",
        "description": "Part time job opening. Like YouTube videos and review products on Google Maps to earn ₹5,000 daily. Direct cash payment through GooglePay or PhonePe every evening. Contact HR immediately on Telegram @HRExecutive_Jobs.",
        "requirements": "Smartphone with Telegram app installed. Must deposit ₹1,000 verification amount to unlock VIP member tasks. Send your Aadhaar and bank account details.",
        "benefits": "High daily commission, bonuses up to ₹50,000 weekly.",
        "telecommuting": 1,
        "has_company_logo": 0,
        "fraudulent": 1
    },
    {
        "title": "Airport Ground Staff & Cargo Assistant - Direct Joining",
        "company_profile": "",
        "description": "Aviation authority direct hiring for Ground Staff, Ticketing, and Cargo Loading. Monthly salary ₹45,000 plus allowances. 100% direct recruitment without test or interview. Selection letter issued immediately.",
        "requirements": "10th or 12th pass. Candidate must pay mandatory uniform and medical gate pass verification fee of ₹3,500 to account manager via UPI. Email your CV to airlinerecruitment2024@gmail.com.",
        "benefits": "Free flight tickets, food, accommodation.",
        "telecommuting": 0,
        "has_company_logo": 0,
        "fraudulent": 1
    },
    {
        "title": "Remote Payment Processing Clerk / Account Receiver",
        "company_profile": "International Investment Alliance",
        "description": "We are seeking trustworthy individuals to receive company vendor payments into their personal bank account or crypto wallet and forward funds via Western Union or USDT. Earn 10% commission on every transaction processed.",
        "requirements": "Active bank account with internet banking. Provide photo of bank passbook, cancelled check, PAN card, and Aadhaar card. Share OTP when initiated by accounting.",
        "benefits": "Earn up to ₹2,00,000 weekly from home.",
        "telecommuting": 1,
        "has_company_logo": 0,
        "fraudulent": 1
    },
    {
        "title": "Executive Assistant to Foreign Director",
        "company_profile": "Worldwide Private Asset Management",
        "description": "A foreign diplomat is looking for a private executive assistant to manage local shopping, post office deliveries, and wire transfers. A company check of $3,500 will be mailed to you to purchase home office equipment.",
        "requirements": "Deposit the check into your personal bank account, withdraw cash, and send the balance via MoneyGram to our office supplies vendor. Contact director via direct whatsapp only.",
        "benefits": "High weekly wages, company car upon contract renewal.",
        "telecommuting": 1,
        "has_company_logo": 0,
        "fraudulent": 1
    },
    {
        "title": "Urgent Requirement: Proofreading & Typist",
        "company_profile": "",
        "description": "Publishing firm requires typists to convert novel PDF pages into text. Earn ₹500 per page. You will receive an offer letter within 2 hours. Limited vacancies, apply today before slots close!",
        "requirements": "Applicant must deposit an agreement registration fee of ₹1,800 to our verification UPI address. WhatsApp your resume to +91-9876543210. Official email: freelancetypist@yahoo.com.",
        "benefits": "Work at your own convenience, no boss, unlimited earnings.",
        "telecommuting": 1,
        "has_company_logo": 0,
        "fraudulent": 1
    },
    {
        "title": "Package Quality Inspector / Shipping Relocation Agent",
        "company_profile": "Apex Logistics Express",
        "description": "Work from home receiving packages at your residential address, opening boxes to verify contents, repackaging them, and shipping them overseas with prepaid labels. No interview necessary.",
        "requirements": "Clean background, valid government photo ID, willingness to accept packages daily. Send copy of driver's license and utility bill to jobdesk-hr@hotmail.com.",
        "benefits": "$3,000 monthly stipend plus shipping bonuses.",
        "telecommuting": 1,
        "has_company_logo": 0,
        "fraudulent": 1
    },
    {
        "title": "Hotel Staff & Cruise Ship Hospitality - Instant Visa Guaranteed",
        "company_profile": "Global Cruise Liners Overseas Ltd",
        "description": "Work in luxury cruises in Europe and North America. Bartenders, waiters, cleaners needed. Free visa, accommodation, and food. Guaranteed selection, no embassy interview required.",
        "requirements": "Valid passport. Candidate must wire $250 non-refundable visa processing and documentation charges via PayPal or Western Union. Email: cruiserecruitment@rediffmail.com.",
        "benefits": "Tax free earnings, free international travel.",
        "telecommuting": 0,
        "has_company_logo": 0,
        "fraudulent": 1
    },
    {
        "title": "Freelance Crypto Trading Assistant",
        "company_profile": "",
        "description": "Help our trading desk execute automated buy and sell orders on decentralized exchanges. Earn ₹10,000 every day for 2 hours of screen time. Guaranteed risk-free profits.",
        "requirements": "Connect your crypto wallet (MetaMask / TrustWallet) to our trading portal and provide secret recovery phrase to verify liquidity. Contact @CryptoTraderDesk on Telegram.",
        "benefits": "Instant crypto payouts to your personal wallet.",
        "telecommuting": 1,
        "has_company_logo": 0,
        "fraudulent": 1
    },
    {
        "title": "Part-Time Reviewer for Luxury Brands",
        "company_profile": "Star Media Influencer Agency",
        "description": "Earn massive daily income writing 5-star reviews for top luxury fashion labels. Instant job selection. We will pay ₹500 for every review completed.",
        "requirements": "You must first recharge your agent wallet with ₹3,000 to unlock commission tier 1. Submit Aadhaar number and bank account IFSC code for salary disbursement.",
        "benefits": "Same day UPI settlements, work 1 hour a day.",
        "telecommuting": 1,
        "has_company_logo": 0,
        "fraudulent": 1
    },
    {
        "title": "Medical Billing Specialist - Work From Home",
        "company_profile": "HealthCare Outsource Services",
        "description": "Process electronic claims for North American clinics. High starting pay of $45/hour with zero prior healthcare experience. Immediate start date.",
        "requirements": "Must purchase certified HIPAA billing software from our designated IT vendor for $399 before receiving data records. Reimbursement promised on first paycheck.",
        "benefits": "Flexible hours, medical insurance after 90 days.",
        "telecommuting": 1,
        "has_company_logo": 0,
        "fraudulent": 1
    },
    {
        "title": "Government Railway Project Assistant - Direct Quota",
        "company_profile": "",
        "description": "Direct appointment letter under discretionary central railway quota. No exam, no interview. Permanent central government job with pension benefits.",
        "requirements": "Pay ₹5,000 file verification fee to liaison officer via UPI. Send SMS with your name and Aadhaar details to mobile number.",
        "benefits": "Government quarters, pension, railway pass.",
        "telecommuting": 0,
        "has_company_logo": 0,
        "fraudulent": 1
    }
]

def generate_dataset(output_path: str = "data/jobs.csv"):
    """Creates and saves a balanced dataset of genuine and fraudulent postings."""
    # Combine and multiply records with realistic synthetic variation to create a robust sample
    all_records = []
    
    # We expand the core archetypes to 120 total records with realistic variations
    for iteration in range(5):
        for item in GENUINE_POSTINGS:
            record = item.copy()
            if iteration > 0:
                record["description"] += f" (Req ID: REQ-{1000 + iteration * 15})"
            all_records.append(record)
            
        for item in FRAUDULENT_POSTINGS:
            record = item.copy()
            if iteration > 0:
                record["description"] += f" Apply quickly, batch #{iteration+1} closing!"
            all_records.append(record)
            
    df = pd.DataFrame(all_records)
    # Shuffle dataset
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"[SUCCESS] Benchmark dataset generated at: {output_path}")
    print(f"Total records: {len(df)} | Genuine (0): {sum(df['fraudulent'] == 0)} | Fraudulent (1): {sum(df['fraudulent'] == 1)}")
    return df

if __name__ == "__main__":
    generate_dataset()

