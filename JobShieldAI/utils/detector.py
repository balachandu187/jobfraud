"""
Rule-Based Scam Detection Engine for JobShield AI

Inspects job postings against high-confidence fraud heuristics covering advance-fee
extortion, identity theft, money-mule laundering, unregulated contact channels and
psychological manipulation.

Design notes
------------
* Each rule contributes a fixed weight; the total is clamped to 100.
* ``CRITICAL`` rules trigger a hard risk floor in ``utils/risk_analyzer.py`` so a
  single severe finding can never be averaged away by a confident ML score.
* Patterns deliberately tolerate the many ways scammers write amounts
  (``₹2,000``, ``Rs 2000``, ``INR 2,000/-``, ``$250``) and use word boundaries so
  that legitimate text such as "bank account details for payroll" (a genuine
  onboarding step) does not fire the identity-theft rule on its own.
"""

import re
from typing import Any, Dict, List

#: Amount fragment reused across financial rules: ₹2,000 / Rs. 2000 / INR 2,000 / $250
_AMOUNT = r"(?:₹|rs\.?|inr|\$|usd)\s?\d[\d,]*(?:\.\d+)?"


class ScamDetector:
    def __init__(self) -> None:
        self.rules: List[Dict[str, Any]] = [
            {
                "id": "UPFRONT_FEE",
                "category": "Financial Scam",
                "severity": "CRITICAL",
                "weight": 35,
                "pattern": re.compile(
                    rf"(?:registration|security|training|software|application|verification|processing|"
                    rf"activation|documentation|agreement|onboarding|file|gate\s*pass|licen[cs]e)\s*"
                    rf"(?:fee|fees|charge|charges|deposit|amount)"
                    rf"|refundable\s*(?:deposit|amount|fee)"
                    rf"|(?:pay|deposit|transfer|wire|remit|send)\s*{_AMOUNT}"
                    rf"|{_AMOUNT}\s*(?:/-)?\s*(?:non-?refundable\s*)?(?:registration|processing|verification|"
                    rf"documentation|visa|security|activation|training)\s*(?:fee|charge|deposit|amount)?"
                    rf"|advance\s*payment|purchase\s*(?:the\s*)?(?:software|certified\s*\w+)"
                    rf"|pay\s*(?:a\s*)?(?:mandatory|minimum|one-?time)\s*(?:\w+\s*){{0,2}}(?:fee|charge|amount|deposit)"
                    rf"|make\s*(?:the\s*)?payment",
                    re.IGNORECASE,
                ),
                "title": "Upfront / Registration Fee Demanded",
                "explanation": (
                    "Legitimate employers never demand registration fees, security deposits, "
                    "training kit charges or software purchase fees from applicants."
                ),
            },
            {
                "id": "GUARANTEED_NO_INTERVIEW",
                "category": "Deceptive Hiring",
                "severity": "HIGH",
                "weight": 25,
                "pattern": re.compile(
                    r"(?:100%|guaranteed)\s*(?:job\s*)?(?:selection|placement|joining|approval)"
                    r"|guaranteed\s*(?:selection|placement|job|visa|profits?)"
                    r"|no\s*(?:written\s*)?(?:exam|test|interview|screening)(?:\s*(?:required|necessary|needed))?"
                    r"|without\s*(?:any\s*)?(?:technical\s*)?(?:interview|test|exam|screening)"
                    r"|direct\s*(?:joining|appointment|recruitment|hiring|selection)"
                    r"|instant\s*(?:joining|selection|appointment|approval)"
                    r"|(?:offer|appointment|selection|joining)\s*letter\s*(?:issued\s*)?within\s*\d+\s*(?:hour|hr|minute|day)"
                    r"|interview\s*(?:is\s*)?(?:waived|not\s*required|not\s*necessary)"
                    r"|selection\s*(?:is\s*)?(?:confirmed|guaranteed)",
                    re.IGNORECASE,
                ),
                "title": "Guaranteed Hiring Without Proper Screening",
                "explanation": (
                    "Genuine corporate jobs require interviews, assessments and credential checks. "
                    "Guaranteed selection or instant appointment letters are classic lures."
                ),
            },
            {
                "id": "SENSITIVE_DATA_THEFT",
                "category": "Identity & Banking Fraud",
                "severity": "CRITICAL",
                "weight": 35,
                "pattern": re.compile(
                    r"\botp\b|one\s*time\s*password|net\s*banking\s*(?:password|login|credential)"
                    r"|(?:share|send|provide|submit|forward)\s*(?:your\s*)?(?:aadhaar|pan|passport|"
                    r"bank\s*(?:account|passbook|details|statement)|cancell?ed\s*cheque|ifsc)"
                    r"|(?:aadhaar|pan\s*card)\s*(?:number|copy|details|photo|card)"
                    r"|crypto\s*wallet|seed\s*phrase|recovery\s*phrase|private\s*key"
                    r"|credit\s*card\s*(?:details|number|cvv)"
                    r"|share\s*(?:the\s*)?(?:otp|code|password)",
                    re.IGNORECASE,
                ),
                "title": "Request for Confidential Banking / Identity Details",
                "explanation": (
                    "Asking applicants to share OTPs, net-banking passwords, Aadhaar/PAN scans, "
                    "cancelled cheques or crypto seed phrases in a job posting is a direct "
                    "identity-theft and cybercrime red flag."
                ),
            },
            {
                "id": "MONEY_MULE_SCHEME",
                "category": "Money Laundering",
                "severity": "CRITICAL",
                "weight": 35,
                "pattern": re.compile(
                    r"(?:receive|accept)\s*(?:company\s*|client\s*)?(?:payments?|funds?|packages?|parcels?)"
                    r"\s*(?:in|into|at)\s*(?:your\s*)?(?:personal\s*)?(?:bank|account|home|address)"
                    r"|forward\s*(?:the\s*)?funds|western\s*union|moneygram"
                    r"|wire\s*(?:the\s*)?(?:balance|funds|money)|cash\s*(?:a\s*)?check\s*and\s*send"
                    r"|\d+\s*%\s*commission\s*on\s*every\s*transaction"
                    r"|deposit\s*the\s*check\s*into\s*your|re-?\s*ship(?:ping)?\s*(?:packages|parcels)"
                    r"|reship|repackag(?:e|ing)\s*(?:them|boxes)|mystery\s*shopper\s*check",
                    re.IGNORECASE,
                ),
                "title": "Suspected Money Mule / Parcel Laundering Scheme",
                "explanation": (
                    "Using personal bank accounts to receive third-party funds and forward them abroad — "
                    "or re-shipping parcels from your home — is money laundering / reshipping fraud, "
                    "and the victim carries criminal liability."
                ),
            },
            {
                "id": "SUSPICIOUS_CHANNELS",
                "category": "Communication Evasion",
                "severity": "HIGH",
                "weight": 20,
                "pattern": re.compile(
                    r"contact\s*(?:\w+\s*){0,2}(?:on|via|through)\s*(?:telegram|whatsapp)"
                    r"|(?:telegram|whatsapp)\s*@|t\.me/"
                    r"|whatsapp\s*(?:only|your\s*(?:resume|cv|documents?))"
                    r"|message\s*(?:\w+\s*){0,2}on\s*(?:telegram|whatsapp)"
                    r"|(?:join|contact)\s*(?:our|the)?\s*(?:telegram|whatsapp)\s*(?:group|channel|number)"
                    r"|\bDM\s*(?:us\s*)?on\s*(?:telegram|whatsapp|instagram)",
                    re.IGNORECASE,
                ),
                "title": "Unregulated Communication Channel (Telegram / WhatsApp Only)",
                "explanation": (
                    "Scammers avoid corporate audit trails by routing applicants to Telegram or "
                    "unverified WhatsApp numbers instead of official email and scheduled calls."
                ),
            },
            {
                "id": "PERSONAL_EMAIL_DOMAIN",
                "category": "Domain Credibility",
                "severity": "MEDIUM",
                "weight": 15,
                "pattern": re.compile(
                    r"[\w.+-]+@(?:gmail|yahoo|hotmail|rediffmail|outlook|live|aol|protonmail|"
                    r"zoho|ymail|mail|gmx|icloud)\.(?:com|in|co\.in|org)",
                    re.IGNORECASE,
                ),
                "title": "Generic Free Webmail Used for Recruitment",
                "explanation": (
                    "Official recruiters write from verified corporate domains (hr@company.com), "
                    "not free webmail such as Gmail, Yahoo or Rediffmail."
                ),
            },
            {
                "id": "EXORBITANT_SALARY_LOW_SKILL",
                "category": "Unrealistic Compensation",
                "severity": "HIGH",
                "weight": 20,
                "pattern": re.compile(
                    r"(?:earn|salary|income|pay)\s*(?:up\s*to\s*)?(?:" + _AMOUNT + r")?\s*"
                    r"(?:\d{1,3}(?:,\d{2,3})+|\d{4,})\s*(?:/-)?\s*"
                    r"(?:to\s*(?:" + _AMOUNT + r")?\s*[\d,]+)?\s*"
                    r"per\s*(?:day|month|hour|week)\b[^.]{0,80}"
                    r"(?:typing|data\s*entry|liking|like\s*you\s*tube|simple\s*(?:ms\s*word|copy|task)"
                    r"|no\s*experience|students|housewives|part[-\s]*time|2\s*hours?)"
                    r"|(?:₹|rs\.?|inr)\s*[\d,]+\s*(?:per|/)\s*(?:day|daily|hour)"
                    r"|daily\s*(?:payout|payment|settlement)"
                    r"|\d+\s*%\s*(?:monthly\s*)?(?:returns?|profits?)\s*guaranteed"
                    r"|risk[-\s]*free\s*profits?"
                    r"|unlimited\s*earnings?|earn\s*massive",
                    re.IGNORECASE,
                ),
                "title": "Unrealistically High Pay for Low-Skill Tasks",
                "explanation": (
                    "Extravagant daily earnings promised for typing, video-liking or surveys are "
                    "predatory bait designed to override the applicant's judgement."
                ),
            },
            {
                "id": "HIGH_PRESSURE_URGENCY",
                "category": "Psychological Manipulation",
                "severity": "MEDIUM",
                "weight": 10,
                "pattern": re.compile(
                    r"urgent\s*hiring!+|immediate\s*hiring!+|apply\s*within\s*\d+\s*hours"
                    r"|limited\s*(?:seats|vacancies|slots|openings)"
                    r"|last\s*chance\s*to\s*apply|slots?\s*(?:are\s*)?(?:closing|limited)"
                    r"|act\s*now|apply\s*(?:today|immediately)\s*before"
                    r"|only\s*\d+\s*(?:seats|vacancies|slots)\s*(?:left|available)",
                    re.IGNORECASE,
                ),
                "title": "High-Pressure Urgency Tactics",
                "explanation": (
                    "Fabricated urgency is used to induce panic and stop candidates from verifying "
                    "the employer or performing due diligence."
                ),
            },
        ]

    def analyze(self, text: str, company: str = "") -> Dict[str, Any]:
        """Scans job text and metadata against all fraud heuristic rules."""
        company = (company or "").strip()
        combined_text = f"{company} {text or ''}".strip()
        detected: List[Dict[str, Any]] = []
        total_weight = 0

        if not company:
            detected.append({
                "id": "MISSING_COMPANY",
                "title": "Missing Company Identity",
                "category": "Company Transparency",
                "severity": "MEDIUM",
                "weight": 10,
                "explanation": (
                    "The posting does not name a verifiable employer, which makes independent "
                    "background verification impossible."
                ),
            })
            total_weight += 10

        for rule in self.rules:
            match = rule["pattern"].search(combined_text)
            if not match:
                continue
            detected.append({
                "id": rule["id"],
                "title": rule["title"],
                "category": rule["category"],
                "severity": rule["severity"],
                "weight": rule["weight"],
                "explanation": rule["explanation"],
                "evidence": " ".join(match.group(0).split())[:120],
            })
            total_weight += rule["weight"]

        severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        detected.sort(key=lambda item: severity_rank.get(item["severity"], 9))

        return {
            "warnings": detected,
            "warning_count": len(detected),
            "rule_score": min(total_weight, 100),
            "rules_evaluated": len(self.rules) + 1,
        }
