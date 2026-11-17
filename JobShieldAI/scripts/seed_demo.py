"""
Seed the JobShield AI audit log with the benchmark scenarios.

Why: on a fresh machine the dashboard and history page are empty, which makes the
project look inert during a demo. This script resets the audit log and inserts the
five documented benchmark cases so the dashboard, trend chart and top-warning
breakdown all have meaningful data.

Usage (from the JobShieldAI directory):
    python scripts/seed_demo.py            # reset + seed
    python scripts/seed_demo.py --keep     # seed without clearing existing rows
"""

import argparse
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from services import ScanPayload, get_service  # noqa: E402

SCENARIOS = [
    {
        "label": "A. Upfront fee scam",
        "expected": "High Risk",
        "payload": ScanPayload(
            job_title="Work From Home Typist & Data Entry",
            company_name="FastCareers Online Services",
            salary_info="₹80,000 per month",
            contact_email="careers.recruitmentdesk@gmail.com",
            instructions="Pay ₹2,000 refundable registration fee to confirm your joining. No interview required.",
            skills="Basic typing, MS Word, Internet browsing",
            job_description=(
                "Congratulations! You are selected for an online work-from-home job with an attractive "
                "salary of ₹80,000 per month. Direct selection letter issued without any interview. "
                "Pay ₹2,000 registration fees to confirm your position today. "
                "Telegram contact @FastCareersAdmin."
            ),
        ),
    },
    {
        "label": "B. Genuine tech role",
        "expected": "Low Risk",
        "payload": ScanPayload(
            job_title="Senior Software Engineer (Python / FastAPI)",
            company_name="ABC Technologies Ltd",
            salary_info="₹14,00,000 - ₹18,00,000 per annum",
            contact_email="talent@abctechnologies.com",
            instructions="Apply through company official careers portal. Technical interview and coding assessment required.",
            skills="Python, FastAPI, PostgreSQL, Docker, Git, REST APIs",
            job_description=(
                "Senior Software Engineer position at ABC Technologies Ltd. Candidates should have solid "
                "Python, backend API engineering, and distributed systems experience. Applicants will "
                "undergo two rounds of technical interviews and credentials verification. "
                "Apply through the company official careers portal."
            ),
        ),
    },
    {
        "label": "C. OTP / identity theft scam",
        "expected": "High Risk",
        "payload": ScanPayload(
            job_title="Back Office Assistant & Payment Coordinator",
            company_name="Apex Global Hires",
            salary_info="₹60,000 monthly",
            contact_email="apexhires@yahoo.com",
            instructions="Send Aadhaar card, bank account number, and share verification OTP when prompted.",
            skills="None required, immediate joining",
            job_description=(
                "Immediate hiring! Guaranteed job placement with daily salary. Send your Aadhaar details, "
                "bank account information, and share verification OTP to complete appointment letter "
                "issuance. Message HR directly on WhatsApp."
            ),
        ),
    },
    {
        "label": "D. Money mule / laundering",
        "expected": "High Risk",
        "payload": ScanPayload(
            job_title="Remote Payment Processing Clerk",
            company_name="International Investment Alliance",
            job_description=(
                "Seeking trustworthy individuals to receive company vendor payments into their personal "
                "bank account and forward funds via Western Union. Earn 10% commission on every "
                "transaction processed. Contact director via direct whatsapp only."
            ),
        ),
    },
    {
        "label": "E. Hard negative (genuine KYC role)",
        "expected": "Low Risk",
        "payload": ScanPayload(
            job_title="Payroll & Compliance Officer",
            company_name="Arthik Solutions",
            contact_email="careers@arthiksolutions.in",
            job_description=(
                "As part of statutory onboarding you will collect and verify new-joiner bank account "
                "details and PAN/Aadhaar documentation, then upload them to the client HRMS under our "
                "ISO 27001 policy. B.Com with 3 years payroll compliance experience. Candidates complete "
                "background verification after a written offer is signed."
            ),
        ),
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the audit log with benchmark scenarios.")
    parser.add_argument("--keep", action="store_true", help="do not clear existing history")
    args = parser.parse_args()

    service = get_service()
    if not service.predictor.is_ready:
        print("[!] Model artifacts missing. Run `python model/train_model.py` first.", file=sys.stderr)
        return 1

    if not args.keep:
        service.clear_history()
        print("[*] Audit log cleared.")

    failures = 0
    for scenario in SCENARIOS:
        result = service.scan(scenario["payload"]).to_dict()
        risk = result["risk_result"]
        ok = risk["risk_level"] == scenario["expected"]
        failures += 0 if ok else 1
        print(
            f"  {'OK ' if ok else 'MISMATCH'} {scenario['label']:34s} "
            f"score={risk['risk_score']:3d} {risk['risk_level']:11s} "
            f"flags={risk['warning_count']}"
        )

    stats = service.statistics()
    print(
        f"\n[SUCCESS] {stats['total_scans']} records | "
        f"avg score {stats['average_risk_score']} | "
        f"low {stats['low_risk_count']} / medium {stats['medium_risk_count']} / high {stats['high_risk_count']}"
    )
    if failures:
        print(f"[!] {failures} scenario(s) did not match their expected tier.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
