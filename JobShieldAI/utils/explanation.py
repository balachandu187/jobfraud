"""
Explanation and Safety Advisory Module for JobShield AI

Turns a risk verdict plus the detected warning IDs into an ordered, actionable
checklist. Every rule that the detector can emit has a matching advisory here — the
previous version silently dropped advice for MISSING_COMPANY, HIGH_PRESSURE_URGENCY
and EXORBITANT_SALARY_LOW_SKILL.
"""

from typing import Any, Dict, List

#: Advisory copy per rule id, ordered by how urgently the reader must act.
_ADVISORIES: Dict[str, str] = {
    "UPFRONT_FEE": (
        "STOP: never transfer money — registration fees, security deposits, training kits "
        "or software licences are never required by a real employer."
    ),
    "SENSITIVE_DATA_THEFT": (
        "PROTECT YOUR CREDENTIALS: never share OTPs, net-banking passwords, Aadhaar/PAN scans, "
        "cancelled cheques or crypto seed phrases. No employer needs them to hire you."
    ),
    "MONEY_MULE_SCHEME": (
        "LEGAL RISK: receiving third-party funds in your personal account and forwarding them, "
        "or re-shipping parcels from home, is money laundering / reshipping fraud. Refuse and report it."
    ),
    "GUARANTEED_NO_INTERVIEW": (
        "QUESTION THE PROCESS: genuine employers always interview and verify candidates. "
        "Ask for the hiring manager's name and a scheduled call."
    ),
    "SUSPICIOUS_CHANNELS": (
        "INSIST ON TRACEABLE CONTACT: request communication from a corporate email domain and "
        "a scheduled video call, not Telegram or an unverified WhatsApp number."
    ),
    "PERSONAL_EMAIL_DOMAIN": (
        "VERIFY THE RECRUITER: check their LinkedIn profile and confirm the email matches the "
        "official company domain before replying."
    ),
    "EXORBITANT_SALARY_LOW_SKILL": (
        "CHECK THE MATH: pay that wildly exceeds market rates for simple work is bait. "
        "Cross-check the salary band on a public salary benchmark."
    ),
    "HIGH_PRESSURE_URGENCY": (
        "SLOW DOWN: artificial deadlines exist to stop you verifying. A real offer survives "
        "a day of due diligence."
    ),
    "MISSING_COMPANY": (
        "IDENTIFY THE EMPLOYER: no verifiable company name means no accountability. "
        "Ask for the registered entity name and CIN/GST number."
    ),
}

_UNIVERSAL_LOW_RISK = [
    "Verify the opening directly on the employer's official careers portal.",
    "Confirm the recruiter writes from an authenticated corporate email domain.",
    "Never share bank credentials, OTPs or identity scans before a signed written offer.",
]

_FALLBACK = [
    "Search '[company name] + job scam' to check for reports from other applicants.",
    "Never click shortened links (bit.ly, tinyurl) sent by an unverified recruiter.",
    "Confirm the registered company name and address on an official registry (MCA/GST).",
]

#: Reporting channels surfaced whenever money or credentials were requested.
_REPORTING = {
    "INDIA": [
        "Report cyber fraud at cybercrime.gov.in or call 1930 immediately if money was transferred.",
        "File a complaint with the National Consumer Helpline (1915) for fraudulent recruitment ads.",
    ],
    "GLOBAL": [
        "Report the posting to the hosting platform (LinkedIn, Indeed, Telegram) for takedown.",
    ],
}


def get_safety_recommendations(
    risk_level: str,
    warnings: List[Dict[str, Any]],
    region: str = "INDIA",
) -> List[str]:
    """Generates tailored, ordered safety advice for a verdict."""
    warning_ids = [str(w.get("id", "")) for w in warnings if w.get("id")]
    unique_ids = list(dict.fromkeys(warning_ids))

    if risk_level == "Low Risk" and not unique_ids:
        return list(_UNIVERSAL_LOW_RISK)

    recommendations = [_ADVISORIES[wid] for wid in unique_ids if wid in _ADVISORIES]

    if risk_level == "Low Risk" and unique_ids:
        # Minor signal only — advise verification without alarming the user.
        recommendations.append(
            "This posting looks largely clean, but complete the checks above before sharing documents."
        )

    if unique_ids:
        recommendations.extend(_REPORTING.get(region, []))
        recommendations.extend(_REPORTING["GLOBAL"])

    if not recommendations:
        recommendations = list(_FALLBACK)

    # De-duplicate while preserving order.
    return list(dict.fromkeys(recommendations))
