"""
Rule-based scam detection engine.

Independent of machine learning: pure pattern matching over the advertisement text.
Each fired rule returns an identifier, a warning name, a severity, a plain-language
explanation, and the quoted evidence that triggered it.

Design notes
------------
* **Presence rules** look for an instruction to *do* something dangerous ("pay ₹2,000",
  "share OTP"). They are weighted by how strong that evidence is on its own.
* **Absence rules** (missing company, vague description) are weak signals. A job board
  scrape often omits the company name, and short ads are common and legal, so these
  carry small weights and can never push an ad to High Risk by themselves.
* Word-boundary patterns keep legitimate postings clean: a payroll role that says "we
  collect new-joiner bank account details under our ISO 27001 policy" does not fire the
  identity-theft rule, but "send your bank passbook photo and OTP" does.
* Rule weights sum to more than 100 by design; the total is clamped because a posting
  can be damning for several independent reasons.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

#: Amount fragment: ₹2,000 / Rs. 2000 / INR 2,000 / $250 / 2000/-
AMOUNT = r"(?:₹|rs\.?|inr|\$|usd)?\s?\d[\d,]*(?:\.\d+)?(?:\s*/-)?"

#: Email domain list considered "free webmail" rather than a corporate domain.
FREE_WEBMAIL = (
    "gmail|yahoo|hotmail|rediffmail|outlook|live|aol|protonmail|proton|zoho|"
    "ymail|mail|gmx|icloud|yandex|tutanota"
)

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


@dataclass
class Rule:
    """A single detection rule."""

    id: str
    flag: str
    severity: str
    weight: int
    explanation: str
    category: str
    pattern: Optional[re.Pattern] = None
    #: Absence rules fire when a field is empty rather than on a text match.
    absence_check: Optional[str] = None


def _compile(expression: str) -> re.Pattern:
    return re.compile(expression, re.IGNORECASE)


class RuleEngine:
    """Evaluates a job advertisement against every fraud heuristic."""

    def __init__(self) -> None:
        self.rules: List[Rule] = [
            # ---------------- Financial -------------------------------
            Rule(
                id="REGISTRATION_FEE",
                flag="Registration fee requested",
                severity="CRITICAL",
                weight=35,
                category="Financial Scam",
                explanation=(
                    "Legitimate employers do not ask candidates to pay registration, "
                    "processing or file charges to secure a job. Any fee request is a "
                    "defining feature of advance-fee recruitment fraud."
                ),
                pattern=_compile(
                    rf"(?:registration|processing|verification|application|file|onboarding)"
                    rf"\s*(?:fee|fees|charge|charges|amount)"
                    rf"|(?:pay|remit)\s*{AMOUNT}[^.]{{0,40}}(?:fee|charge|deposit)"
                    rf"|{AMOUNT}\s*(?:registration|processing|verification|application)\s*"
                    rf"(?:fee|charge|amount)"
                ),
            ),
            Rule(
                id="ADVANCE_PAYMENT",
                flag="Advance payment demanded before joining",
                severity="CRITICAL",
                weight=32,
                category="Financial Scam",
                explanation=(
                    "Money requested before an employment contract exists — for training, "
                    "kits, uniforms or tooling — is a classic advance-fee scheme."
                ),
                pattern=_compile(
                    rf"(?:advance\s*payment|upfront\s*(?:payment|fee|amount)"
                    rf"|pay\s*(?:in\s*)?advance"
                    rf"|(?:purchase|buy)\s*(?:the\s*)?(?:software|kit|certified|tool)"
                    rf"|training\s*(?:kit|fee|charge)"
                    rf"|(?:uniform|gate\s*pass)\s*(?:fee|charge|deposit))"
                ),
            ),
            Rule(
                id="SECURITY_DEPOSIT",
                flag="Security deposit or refundable deposit requested",
                severity="CRITICAL",
                weight=30,
                category="Financial Scam",
                explanation=(
                    "'Refundable' deposits are rarely refunded. Indian labour practice does "
                    "not require candidates to deposit money with a prospective employer."
                ),
                pattern=_compile(
                    rf"(?:security|refundable|caution|safety)\s*(?:deposit|amount|money)"
                    rf"|deposit\s*{AMOUNT}"
                    rf"|{AMOUNT}\s*(?:refundable\s*)?deposit"
                    rf"|(?:recharge|top\s*up)\s*(?:your\s*)?(?:wallet|account)\s*(?:with)?\s*{AMOUNT}"
                ),
            ),
            # ---------------- Hiring process --------------------------
            Rule(
                id="GUARANTEED_SELECTION",
                flag="Guaranteed selection promised",
                severity="HIGH",
                weight=25,
                category="Deceptive Hiring",
                explanation=(
                    "No genuine employer can guarantee selection before assessing a "
                    "candidate. Guarantees are used to bypass the applicant's judgement."
                ),
                pattern=_compile(
                    r"(?:100%\s*(?:job\s*)?(?:guaranteed|selection|placement)"
                    r"|guaranteed\s*(?:job|selection|placement|visa|approval|joining)"
                    r"|selection\s*(?:is\s*)?(?:guaranteed|confirmed)"
                    r"|(?:direct|confirmed)\s*(?:appointment|joining)\s*letter"
                    r"|direct\s*(?:recruitment|quota|entry))"
                ),
            ),
            Rule(
                id="NO_INTERVIEW",
                flag="No interview or screening required",
                severity="HIGH",
                weight=25,
                category="Deceptive Hiring",
                explanation=(
                    "Real hiring involves an interview or assessment. Offers extended "
                    "without any screening exist to avoid verifying the candidate — and to "
                    "avoid the candidate verifying the employer."
                ),
                pattern=_compile(
                    r"(?:no\s*(?:written\s*)?(?:interview|exam|test|screening)(?:\s*(?:required|necessary|needed))?"
                    r"|without\s*(?:any\s*)?(?:technical\s*)?(?:interview|test|exam|screening)"
                    r"|interview\s*(?:is\s*)?(?:waived|not\s*(?:required|necessary))"
                    r"|(?:offer|appointment)\s*letter\s*(?:issued\s*)?within\s*\d+\s*(?:hour|hr|minute|day))"
                ),
            ),
            Rule(
                id="UNREALISTIC_SALARY",
                flag="Unrealistic salary for the stated skill level",
                severity="HIGH",
                weight=20,
                category="Unrealistic Compensation",
                explanation=(
                    "Pay far above market rate for simple or unskilled work is bait. "
                    "Genuine salaries are bounded by the role's market value."
                ),
                pattern=_compile(
                    r"(?:(?:earn|salary|income|pay)\s*(?:up\s*to\s*)?(?:₹|rs\.?|inr|\$)?\s*"
                    r"\d{1,3}(?:,\d{2,3})+\s*(?:to\s*(?:₹|rs\.?)?\s*[\d,]+)?\s*"
                    r"per\s*(?:day|month|week|hour)[^.]{0,90}"
                    r"(?:typing|data\s*entry|liking|like\s*(?:you\s*)?tube|copy\s*paste"
                    r"|simple\s*(?:task|work)|no\s*experience|students|housewives|part[-\s]*time|2\s*hours?)"
                    r"|(?:₹|rs\.?|inr)\s*[\d,]+\s*(?:per|/)\s*(?:day|daily|hour)\b"
                    r"|daily\s*(?:payout|payment|settlement|income)"
                    r"|\d{1,2}\s*%\s*(?:monthly\s*)?(?:returns?|profits?)\s*(?:guaranteed)?"
                    r"|risk[-\s]*free\s*profits?)"
                ),
            ),
            Rule(
                id="URGENT_PRESSURE",
                flag="High-pressure urgency tactics",
                severity="MEDIUM",
                weight=12,
                category="Psychological Manipulation",
                explanation=(
                    "Fabricated deadlines are used to stop candidates doing due diligence. "
                    "A real offer survives a day of verification."
                ),
                pattern=_compile(
                    r"(?:urgent\s*hiring!+|immediate\s*hiring!+|apply\s*within\s*\d+\s*hours"
                    r"|limited\s*(?:seats|vacancies|slots|openings)"
                    r"|last\s*chance\s*to\s*apply|slots?\s*(?:are\s*)?(?:closing|limited)"
                    r"|act\s*now|only\s*\d+\s*(?:seats|vacancies|slots)\s*(?:left|available)"
                    r"|apply\s*(?:today|immediately)\s*before)"
                ),
            ),
            # ---------------- Contact & identity ----------------------
            Rule(
                id="PERSONAL_EMAIL",
                flag="Free webmail address used for recruitment",
                severity="MEDIUM",
                weight=12,
                category="Domain Credibility",
                explanation=(
                    "Corporate recruiters write from a company domain. A free Gmail/Yahoo "
                    "address is not proof of fraud on its own — small businesses do it — but "
                    "it removes a key way to verify the employer."
                ),
                pattern=_compile(rf"[\w.+-]+@(?:{FREE_WEBMAIL})\.(?:com|in|co\.in|org|net|me)"),
            ),
            Rule(
                id="SUSPICIOUS_CHANNEL",
                flag="Applicants routed to Telegram or WhatsApp",
                severity="HIGH",
                weight=18,
                category="Communication Evasion",
                explanation=(
                    "Messaging apps leave no corporate audit trail and cannot be verified. "
                    "Recruiters who insist on them are avoiding accountability."
                ),
                pattern=_compile(
                    r"(?:contact\s*(?:\w+\s*){0,2}(?:on|via|through)\s*(?:telegram|whatsapp)"
                    r"|(?:telegram|whatsapp)\s*@|t\.me/"
                    r"|whatsapp\s*(?:only|your\s*(?:resume|cv|documents?))"
                    r"|message\s*(?:\w+\s*){0,2}on\s*(?:telegram|whatsapp))"
                ),
            ),
            Rule(
                id="OTP_REQUEST",
                flag="OTP or verification code requested",
                severity="CRITICAL",
                weight=35,
                category="Identity & Banking Fraud",
                explanation=(
                    "No employer ever needs an OTP. It exists solely to authorise a "
                    "transaction or account change, so sharing one hands over your account."
                ),
                pattern=_compile(
                    r"(?:\botp\b|one\s*time\s*password|share\s*(?:the\s*)?(?:otp|code)"
                    r"|verification\s*(?:otp|code))"
                ),
            ),
            Rule(
                id="BANK_DETAILS_REQUEST",
                flag="Bank account details or credentials requested",
                severity="CRITICAL",
                weight=32,
                category="Identity & Banking Fraud",
                explanation=(
                    "Salary accounts are set up by HR after joining, using a cancelled cheque "
                    "— never by sending net-banking passwords or passbook photos over chat."
                ),
                pattern=_compile(
                    r"(?:(?:share|send|provide|submit|forward)\s*(?:your\s*)?"
                    r"(?:bank\s*(?:account|passbook|details|statement)|ifsc|net\s*banking"
                    r"|cancell?ed\s*cheque|upi\s*(?:id|pin)|atm\s*pin|cvv)"
                    r"|net\s*banking\s*(?:password|login|credential)"
                    r"|bank\s*passbook\s*(?:photo|copy|details))"
                ),
            ),
            Rule(
                id="IDENTITY_DOCUMENTS_REQUEST",
                flag="Sensitive identity documents requested upfront",
                severity="HIGH",
                weight=22,
                category="Identity & Banking Fraud",
                explanation=(
                    "Aadhaar, PAN and passport copies are collected during formal onboarding "
                    "under data-protection rules — not demanded over WhatsApp before an offer."
                ),
                pattern=_compile(
                    r"(?:(?:send|share|submit|provide|whatsapp|email)\s*(?:your\s*|the\s*)?"
                    r"(?:aadhaar|aadhar|pan\s*card|passport|driving\s*licen[cs]e|voter\s*id)"
                    r"\s*(?:number|copy|details|photo|card|scan)?"
                    r"|(?:aadhaar|aadhar)\s*(?:number|copy|details|card)\s*(?:and|,|&)?"
                    r"\s*(?:pan|bank|passbook)?)"
                ),
            ),
            Rule(
                id="MONEY_MULE",
                flag="Money mule or parcel reshipping scheme",
                severity="CRITICAL",
                weight=34,
                category="Money Laundering",
                explanation=(
                    "Receiving third-party funds into your personal account and forwarding them, "
                    "or re-shipping parcels from your home, is money laundering / reshipping "
                    "fraud. The victim — not just the scammer — carries criminal liability."
                ),
                pattern=_compile(
                    r"(?:(?:receive|accept)\s*(?:company\s*|client\s*)?(?:payments?|funds?|packages?|parcels?)"
                    r"\s*(?:in|into|at)\s*(?:your\s*)?(?:personal\s*)?(?:bank|account|home|address)"
                    r"|forward\s*(?:the\s*)?funds|western\s*union|moneygram"
                    r"|wire\s*(?:the\s*)?(?:balance|funds|money)"
                    r"|cash\s*(?:a\s*)?check\s*and\s*send"
                    r"|\d+\s*%\s*commission\s*on\s*every\s*transaction"
                    r"|deposit\s*the\s*check\s*into\s*your"
                    r"|re-?\s*ship(?:ping)?\s*(?:packages?|parcels?)|reship"
                    r"|repackag(?:e|ing)\s*(?:them|boxes?))"
                ),
            ),
            # ---------------- Absence signals (deliberately weak) -----
            Rule(
                id="MISSING_COMPANY",
                flag="Company information missing",
                severity="LOW",
                weight=8,
                category="Company Transparency",
                absence_check="company_name",
                explanation=(
                    "Without an employer name the posting cannot be verified. On its own "
                    "this is common on job boards, so it is treated as a weak signal."
                ),
            ),
            Rule(
                id="VAGUE_DESCRIPTION",
                flag="Job description is vague or very short",
                severity="LOW",
                weight=8,
                category="Company Transparency",
                absence_check="job_description",
                explanation=(
                    "Genuine postings describe duties, requirements and the hiring process. "
                    "A few generic lines give nothing to verify — a weak signal only."
                ),
            ),
        ]

    # ------------------------------------------------------------------
    def analyze(
        self,
        text: str,
        company: str = "",
        *,
        min_description_chars: int = 120,
    ) -> Dict[str, Any]:
        """
        Runs every rule against the advertisement.

        Args:
            text: the advertisement text (description + any metadata).
            company: employer name, used by the absence rule.
            min_description_chars: below this length the description counts as vague.

        Returns:
            dict with `flags`, `rule_score` (0-100), `severity_counts`, `rules_evaluated`.
        """
        body = (text or "").strip()
        company = (company or "").strip()
        haystack = f"{company} {body}".strip()
        flags: List[Dict[str, Any]] = []
        total = 0

        for rule in self.rules:
            evidence = ""
            fired = False

            if rule.absence_check == "company_name":
                fired = not company
                evidence = "" if company else "employer name not provided"
            elif rule.absence_check == "job_description":
                fired = len(body) < min_description_chars
                evidence = f"description is {len(body)} characters"
            elif rule.pattern is not None:
                match = rule.pattern.search(haystack)
                if match:
                    fired = True
                    evidence = " ".join(match.group(0).split())[:160]

            if not fired:
                continue

            flags.append({
                "id": rule.id,
                "flag": rule.flag,
                "severity": rule.severity,
                "weight": rule.weight,
                "category": rule.category,
                "explanation": rule.explanation,
                "evidence": evidence,
                # Alias so the existing UI, which renders `title`, keeps working.
                "title": rule.flag,
            })
            total += rule.weight

        flags.sort(key=lambda item: (SEVERITY_ORDER.get(item["severity"], 9), -item["weight"]))

        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for flag in flags:
            severity_counts[flag["severity"]] += 1

        return {
            "flags": flags,
            "rule_score": min(total, 100),
            "raw_rule_total": total,
            "severity_counts": severity_counts,
            "rules_evaluated": len(self.rules),
        }

    def catalogue(self) -> List[Dict[str, Any]]:
        """Rule metadata for the /api/rules documentation endpoint."""
        return [
            {
                "id": rule.id,
                "flag": rule.flag,
                "severity": rule.severity,
                "weight": rule.weight,
                "category": rule.category,
                "explanation": rule.explanation,
                "type": "absence" if rule.absence_check else "pattern",
            }
            for rule in self.rules
        ]


_engine: Optional[RuleEngine] = None


def get_rule_engine() -> RuleEngine:
    """Process-wide singleton — rule patterns are compiled once."""
    global _engine
    if _engine is None:
        _engine = RuleEngine()
    return _engine
