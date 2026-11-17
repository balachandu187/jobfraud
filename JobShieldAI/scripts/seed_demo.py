"""
Seed the audit log with the documented benchmark scenarios.

On a fresh database the dashboard and history page are empty, which makes the project
look inert during a demo. This script clears the log and inserts the benchmark cases so
the dashboard cards, donut chart, flag breakdown and 7-day trend all have real data.

Works against the **v3 backend** (SQLAlchemy) by default.

Usage (from the JobShieldAI directory):
    python scripts/seed_demo.py            # reset + seed
    python scripts/seed_demo.py --keep     # seed without clearing existing rows
    python scripts/seed_demo.py --legacy   # seed the old v2 (api.py) database instead
"""

from __future__ import annotations

import argparse
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

SCENARIOS = [
    {
        "label": "A. Upfront fee scam",
        "expect": "High Risk",
        "body": {
            "job_title": "Work From Home Typist & Data Entry",
            "company_name": "FastCareers Online Services",
            "salary": "₹80,000 per month",
            "contact_email": "careers.recruitmentdesk@gmail.com",
            "instructions": (
                "Pay ₹2,000 refundable registration fee to confirm your joining. "
                "No interview required."
            ),
            "job_description": (
                "Congratulations! You are selected for an online work-from-home job with an "
                "attractive salary of ₹80,000 per month. Direct selection letter issued without "
                "any interview. Pay ₹2,000 registration fees to confirm your position today. "
                "Telegram contact @FastCareersAdmin."
            ),
        },
    },
    {
        "label": "B. Genuine tech role",
        "expect": "Low Risk",
        "body": {
            "job_title": "Senior Software Engineer (Python / FastAPI)",
            "company_name": "ABC Technologies Ltd",
            "salary": "₹14,00,000 - ₹18,00,000 per annum",
            "contact_email": "talent@abctechnologies.com",
            "instructions": (
                "Apply through the official careers portal. Technical interview and coding "
                "assessment required."
            ),
            "job_description": (
                "Senior Software Engineer position at ABC Technologies Ltd. Candidates should "
                "have solid Python, backend API engineering, and distributed systems experience. "
                "Applicants will undergo two rounds of technical interviews and credentials "
                "verification. Apply through the company official careers portal."
            ),
        },
    },
    {
        "label": "C. OTP / identity theft",
        "expect": "High Risk",
        "body": {
            "job_title": "Back Office Assistant & Payment Coordinator",
            "company_name": "Apex Global Hires",
            "salary": "₹60,000 monthly",
            "contact_email": "apexhires@yahoo.com",
            "instructions": "Send Aadhaar card, bank account number, and share verification OTP.",
            "job_description": (
                "Immediate hiring! Guaranteed job placement with daily salary. Send your Aadhaar "
                "details, bank account information, and share verification OTP to complete "
                "appointment letter issuance. Message HR directly on WhatsApp."
            ),
        },
    },
    {
        "label": "D. Money mule / laundering",
        "expect": "High Risk",
        "body": {
            "job_title": "Remote Payment Processing Clerk",
            "company_name": "International Investment Alliance",
            "job_description": (
                "Seeking trustworthy individuals to receive company vendor payments into their "
                "personal bank account and forward funds via Western Union. Earn 10% commission "
                "on every transaction processed. Contact director via direct whatsapp only."
            ),
        },
    },
    {
        "label": "E. Hard negative (real KYC role)",
        "expect": "Low Risk",
        "body": {
            "job_title": "Payroll & Compliance Officer",
            "company_name": "Arthik Solutions",
            "contact_email": "careers@arthiksolutions.in",
            "job_description": (
                "As part of statutory onboarding you will collect and verify new-joiner bank "
                "account details and PAN/Aadhaar documentation, then upload them to the client "
                "HRMS under our ISO 27001 policy. B.Com with 3 years payroll compliance "
                "experience. Candidates complete background verification after a written offer "
                "is signed."
            ),
        },
    },
]


def seed_v3(keep: bool) -> int:
    """Seeds the SQLAlchemy-backed database directly (no running server needed)."""
    from backend.database import crud
    from backend.database.connection import init_db, session_scope
    from backend.services.scan_service import ScanInput, get_scan_service

    init_db()
    service = get_scan_service()
    if not service.ml.is_ready:
        print("[!] Model artifacts missing. Run: python -m backend.ml.train_model",
              file=sys.stderr)
        return 1

    failures = 0
    with session_scope() as db:
        if not keep:
            removed = crud.delete_all_scans(db)
            print(f"[*] Cleared {removed} existing record(s).")

        for scenario in SCENARIOS:
            body = scenario["body"]
            data = ScanInput(
                job_description=body["job_description"],
                job_title=body.get("job_title", ""),
                company_name=body.get("company_name", ""),
                salary=body.get("salary", ""),
                contact_email=body.get("contact_email", ""),
                extra=body.get("instructions", ""),
            )
            result = service.execute(db, data)
            ok = result["risk_level"] == scenario["expect"]
            failures += 0 if ok else 1
            print(
                f"  {'OK ' if ok else 'MISMATCH'} {scenario['label']:32s} "
                f"score={result['risk_score']:3d} {result['risk_level']:11s} "
                f"flags={len(result['rule_based_flags'])}"
            )

        stats = crud.statistics(db)
        print(
            f"\n[SUCCESS] {stats['total_scans']} records | avg {stats['average_risk_score']} | "
            f"low {stats['low_risk_count']} / medium {stats['medium_risk_count']} / "
            f"high {stats['high_risk_count']}"
        )

    if failures:
        print(f"[!] {failures} scenario(s) did not match their expected tier.", file=sys.stderr)
        return 1
    return 0


def seed_legacy(keep: bool) -> int:
    """Seeds the pre-SQLAlchemy database used by api.py."""
    from services import ScanPayload, get_service  # noqa: WPS433 - legacy module

    service = get_service()
    if not service.predictor.is_ready:
        print("[!] Model artifacts missing. Run: python model/train_model.py", file=sys.stderr)
        return 1

    if not keep:
        service.clear_history()
        print("[*] Cleared the legacy audit log.")

    failures = 0
    for scenario in SCENARIOS:
        body = scenario["body"]
        payload = ScanPayload(
            job_description=body["job_description"],
            job_title=body.get("job_title", ""),
            company_name=body.get("company_name", ""),
            salary_info=body.get("salary", ""),
            contact_email=body.get("contact_email", ""),
            instructions=body.get("instructions", ""),
        )
        result = service.scan(payload).to_dict()
        ok = result["risk_result"]["risk_level"] == scenario["expect"]
        failures += 0 if ok else 1
        print(
            f"  {'OK ' if ok else 'MISMATCH'} {scenario['label']:32s} "
            f"score={result['risk_result']['risk_score']:3d} "
            f"{result['risk_result']['risk_level']:11s}"
        )

    stats = service.statistics()
    print(f"\n[SUCCESS] {stats['total_scans']} records")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the JobShield AI audit log.")
    parser.add_argument("--keep", action="store_true", help="do not clear existing rows")
    parser.add_argument("--legacy", action="store_true", help="seed the v2 (api.py) database")
    args = parser.parse_args()

    return seed_legacy(args.keep) if args.legacy else seed_v3(args.keep)


if __name__ == "__main__":
    raise SystemExit(main())
