"""
Rule-Based Scam Detection Engine for JobShield AI
Inspects job postings against high-confidence fraud heuristics, financial extortion patterns,
phishing indicators, and identity theft red flags.
"""

import re
from typing import List, Dict, Any

class ScamDetector:
    def __init__(self):
        # Compiled regex patterns for performance
        self.rules = [
            {
                "id": "UPFRONT_FEE",
                "category": "Financial Scam",
                "severity": "CRITICAL",
                "weight": 35,
                "pattern": re.compile(
                    r"(registration\s*fee|security\s*deposit|training\s*fee|software\s*fee|application\s*fee|"
                    r"verification\s*fee|refundable\s*deposit|pay\s*(₹|\$|rs\.?|inr)?\s*\d+|deposit\s*(₹|\$|rs\.?|inr)?\s*\d+|"
                    r"advance\s*payment|purchase\s*software|wire\s*\$\d+)",
                    re.IGNORECASE
                ),
                "title": "Upfront / Registration Fee Demanded",
                "explanation": "Legitimate employers never demand registration fees, security deposits, or software purchase charges from job applicants."
            },
            {
                "id": "GUARANTEED_NO_INTERVIEW",
                "category": "Deceptive Hiring",
                "severity": "HIGH",
                "weight": 25,
                "pattern": re.compile(
                    r"(100%\s*guaranteed\s*selection|no\s*interview(\s*required)?|direct\s*joining|direct\s*appointment|"
                    r"instant\s*joining|no\s*exam\s*no\s*interview|without\s*any\s*technical\s*interview|"
                    r"offer\s*letter\s*within\s*\d+\s*(hours|minutes))",
                    re.IGNORECASE
                ),
                "title": "Guaranteed Hiring Without Proper Screening",
                "explanation": "Genuine corporate jobs require technical evaluations, credential checks, and interviews. Promises of instant appointment letters indicate fraudulent lures."
            },
            {
                "id": "SENSITIVE_DATA_THEFT",
                "category": "Identity & Banking Fraud",
                "severity": "CRITICAL",
                "weight": 35,
                "pattern": re.compile(
                    r"(otp|one\s*time\s*password|aadhaar|pan\s*card|bank\s*passbook|cancelled\s*cheque|"
                    r"net\s*banking|crypto\s*wallet|seed\s*phrase|recovery\s*phrase|credit\s*card\s*details|"
                    r"share\s*otp|send\s*bank\s*details)",
                    re.IGNORECASE
                ),
                "title": "Request for Confidential Banking / Identity Details",
                "explanation": "Asking for OTPs, internet banking passwords, Aadhaar, or crypto seed phrases in a job posting is a direct identity theft and cybercrime red flag."
            },
            {
                "id": "SUSPICIOUS_CHANNELS",
                "category": "Communication Evasion",
                "severity": "HIGH",
                "weight": 20,
                "pattern": re.compile(
                    r"(contact\s*(on|via)?\s*telegram|telegram\s*@|t\.me/|whatsapp\s*only|"
                    r"whatsapp\s*your\s*resume\s*to\s*\+?\d+|message\s*on\s*whatsapp)",
                    re.IGNORECASE
                ),
                "title": "Unregulated Communication Channel (Telegram / WhatsApp Only)",
                "explanation": "Scammers avoid corporate tracking by routing applicants to encrypted personal messaging apps like Telegram or unverified WhatsApp numbers."
            },
            {
                "id": "PERSONAL_EMAIL_DOMAIN",
                "category": "Domain Credibility",
                "severity": "MEDIUM",
                "weight": 15,
                "pattern": re.compile(
                    r"[\w\.-]+@(gmail\.com|yahoo\.com|hotmail\.com|rediffmail\.com|outlook\.com|live\.com|aol\.com)",
                    re.IGNORECASE
                ),
                "title": "Generic Free Webmail Used for Recruitment",
                "explanation": "Official recruiters communicate from verified enterprise domains (e.g., hr@company.com), not generic free webmail services like Gmail, Yahoo, or Rediffmail."
            },
            {
                "id": "EXORBITANT_SALARY_LOW_SKILL",
                "category": "Unrealistic Compensation",
                "severity": "HIGH",
                "weight": 20,
                "pattern": re.compile(
                    r"(earn\s*(₹|\$|rs\.?|inr)?\s*(5[0-9],000|[6-9][0-9],000|[1-9][0-9]{2},000)\s*(daily|per\s*day|per\s*hour|a\s*day)|"
                    r"earn\s*(₹|\$)?\s*80,000\s*to\s*1,50,000.*(typing|data\s*entry|liking\s*videos))",
                    re.IGNORECASE
                ),
                "title": "Unrealistically High Pay for Low-Skill Tasks",
                "explanation": "Extravagant daily or monthly earnings promised for basic typing, simple surveys, or video-liking are designed as predatory baits."
            },
            {
                "id": "HIGH_PRESSURE_URGENCY",
                "category": "Psychological Manipulation",
                "severity": "MEDIUM",
                "weight": 10,
                "pattern": re.compile(
                    r"(urgent\s*hiring!+|immediate\s*hiring!+|apply\s*within\s*\d+\s*hours|limited\s*seats|last\s*chance\s*to\s*apply|"
                    r"slots\s*closing\s*today|act\s*now)",
                    re.IGNORECASE
                ),
                "title": "High-Pressure Urgency Tactics",
                "explanation": "Scammers fabricate false urgency to induce panic and prevent candidates from performing due diligence or verifying the opportunity."
            },
            {
                "id": "MONEY_MULE_SCHEME",
                "category": "Money Laundering",
                "severity": "CRITICAL",
                "weight": 35,
                "pattern": re.compile(
                    r"(receive\s*(company\s*)?(payments|funds)\s*into\s*your\s*personal\s*bank|forward\s*funds|western\s*union|"
                    r"moneygram|wire\s*transfer\s*balance|cash\s*a\s*check\s*and\s*send|10%\s*commission\s*on\s*every\s*transaction)",
                    re.IGNORECASE
                ),
                "title": "Suspected Money Mule / Check Laundering Scheme",
                "explanation": "Using personal bank accounts to receive third-party funds and forward them is illegal money laundering (money mule recruitment)."
            }
        ]

    def analyze(self, text: str, company: str = "") -> Dict[str, Any]:
        """
        Scans job text and metadata against all fraud heuristic rules.
        """
        combined_text = f"{company} {text}".strip()
        detected_warnings = []
        total_rule_score = 0

        # Check for missing company details
        if not company or company.strip() == "":
            rule_warning = {
                "id": "MISSING_COMPANY",
                "title": "Missing Company Identity",
                "category": "Company Transparency",
                "severity": "MEDIUM",
                "weight": 10,
                "explanation": "The posting does not state a verifiable employer or business entity, making background verification impossible."
            }
            detected_warnings.append(rule_warning)
            total_rule_score += rule_warning["weight"]

        for rule in self.rules:
            matches = rule["pattern"].findall(combined_text)
            if matches:
                warning = {
                    "id": rule["id"],
                    "title": rule["title"],
                    "category": rule["category"],
                    "severity": rule["severity"],
                    "weight": rule["weight"],
                    "explanation": rule["explanation"]
                }
                detected_warnings.append(warning)
                total_rule_score += rule["weight"]

        # Normalize rule score to a max of 100
        rule_score_normalized = min(total_rule_score, 100)

        return {
            "warnings": detected_warnings,
            "warning_count": len(detected_warnings),
            "rule_score": rule_score_normalized
        }

