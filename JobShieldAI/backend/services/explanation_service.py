"""
Explanation and safety-recommendation service.

Two responsibilities:

1. **Deterministic recommendations** — always available, derived from the fired rules.
   This is the source of truth for advice; it does not depend on any model.
2. **Optional Ollama narrative** — a plain-language summary layered on top.

Hard rules for the LLM path
---------------------------
* It is never the classifier: the verdict is already final before Ollama is called.
* It cannot change the score, the tier or the flag list.
* Its output is validated and trimmed; on any failure the deterministic text is used.
* Only the advertisement-derived summary is sent — no personal data, no user identity,
  no IP or session information.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

import requests

from backend.config import settings

logger = logging.getLogger(__name__)

#: Advisory copy per rule id, ordered by urgency.
ADVISORIES: Dict[str, str] = {
    "OTP_REQUEST": (
        "NEVER share an OTP, even with someone claiming to be from the company or your bank. "
        "An OTP authorises a transaction; sharing it is how accounts are emptied."
    ),
    "BANK_DETAILS_REQUEST": (
        "Do not send bank passbook photos, net-banking passwords, UPI PINs or cancelled "
        "cheques over chat. Salary accounts are opened by HR after you join."
    ),
    "REGISTRATION_FEE": (
        "Do not pay any registration, processing or file fee. A legitimate employer never "
        "charges a candidate to be considered for a job."
    ),
    "ADVANCE_PAYMENT": (
        "Do not pay in advance for training kits, software, uniforms or gate passes. "
        "Employers bear these costs."
    ),
    "SECURITY_DEPOSIT": (
        "'Refundable' security deposits are a standard advance-fee trap and are rarely "
        "returned. Refuse and report the posting."
    ),
    "IDENTITY_DOCUMENTS_REQUEST": (
        "Do not send Aadhaar, PAN or passport scans before a signed written offer. Share "
        "them only through an official onboarding portal."
    ),
    "GUARANTEED_SELECTION": (
        "Treat any guaranteed selection or 'direct appointment letter' as fraud. Hiring "
        "always involves assessment of your skills."
    ),
    "NO_INTERVIEW": (
        "Insist on a real interview with the hiring manager. Offers without any screening "
        "exist to avoid verification."
    ),
    "SUSPICIOUS_CHANNEL": (
        "Ask for contact from a corporate email address and a scheduled call. Refuse to "
        "continue on Telegram or an unverified WhatsApp number."
    ),
    "PERSONAL_EMAIL": (
        "Check the recruiter on LinkedIn and confirm the email matches the company's "
        "official domain before replying."
    ),
    "UNREALISTIC_SALARY": (
        "Compare the offer against market rates for that role. Pay far above market rate "
        "for simple work is bait."
    ),
    "URGENT_PRESSURE": (
        "Slow down. Artificial urgency exists to stop you verifying the employer; a genuine "
        "offer will still be there tomorrow."
    ),
    "MISSING_COMPANY": (
        "Ask for the registered legal entity name and its GST or CIN number, then verify "
        "them on the MCA portal."
    ),
    "VAGUE_DESCRIPTION": (
        "Request the full job description, reporting manager and hiring process in writing."
    ),
}

UNIVERSAL_CHECKS = [
    "Verify the opening on the employer's official careers page, not only on the job board.",
    "Confirm the recruiter writes from an authenticated company email domain.",
    "Never share bank credentials, OTPs or identity documents before a signed written offer.",
]

REPORTING_STEPS = [
    "Report cyber fraud in India at cybercrime.gov.in or call 1930 if money was already transferred.",
    "Report the posting to the hosting platform so it can be taken down.",
]


class ExplanationService:
    """Builds recommendations and optional LLM narratives."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self.base_url = (base_url or settings.ollama_url).rstrip("/")
        self.model_name = model_name or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout

    # ------------------------------------------------------------------
    # Deterministic recommendations
    # ------------------------------------------------------------------
    def recommendations(self, risk_level: str, flags: List[Dict[str, Any]]) -> List[str]:
        """Per-rule advice plus a verification checklist. Never empty."""
        rule_ids: List[str] = []
        for flag in flags:
            rule_id = flag.get("id")
            if rule_id and rule_id not in rule_ids:
                rule_ids.append(rule_id)

        if not rule_ids and risk_level == "Low Risk":
            return list(UNIVERSAL_CHECKS)

        ordered = [ADVISORIES[rule_id] for rule_id in rule_ids if rule_id in ADVISORIES]

        if not ordered:
            ordered = [
                "Search the company name together with the word 'scam' to check for "
                "reports from other applicants.",
                "Do not click shortened links sent by an unverified recruiter.",
            ]

        ordered.extend(REPORTING_STEPS)
        # De-duplicate while preserving order.
        return list(dict.fromkeys(ordered))

    # ------------------------------------------------------------------
    # Ollama (optional)
    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        try:
            response = requests.get(
                f"{self.base_url}/api/tags", timeout=settings.ollama_health_timeout
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def list_models(self) -> List[str]:
        try:
            response = requests.get(
                f"{self.base_url}/api/tags", timeout=settings.ollama_health_timeout
            )
            if response.status_code == 200:
                return [
                    model.get("name", "")
                    for model in response.json().get("models", [])
                    if model.get("name")
                ]
        except (requests.RequestException, ValueError):
            pass
        return []

    # ------------------------------------------------------------------
    def explain(
        self,
        *,
        job_title: str,
        company: str,
        risk_level: str,
        risk_score: int,
        flags: List[Dict[str, Any]],
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Returns {"available", "text", "source", "model"}.

        Always returns usable text: the deterministic summary is the fallback.
        """
        fallback_text = self._template_explanation(risk_level, risk_score, flags)

        if not self.is_available():
            return {
                "available": False,
                "text": fallback_text,
                "source": "rule-based fallback (Ollama offline)",
                "model": None,
            }

        installed = self.list_models()
        model = model_name or self.model_name
        if installed and model not in installed:
            model = installed[0]  # prefer what is actually pulled over a 404

        prompt = self._build_prompt(job_title, company, risk_level, risk_score, flags)

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2, "num_predict": 220},
                },
                timeout=self.timeout,
            )
            if response.status_code == 200:
                text = self._sanitise(response.json().get("response", ""))
                if text:
                    return {
                        "available": True,
                        "text": text,
                        "source": f"Ollama ({model})",
                        "model": model,
                    }
            elif response.status_code == 404:
                return {
                    "available": False,
                    "text": fallback_text,
                    "source": f"rule-based fallback (model '{model}' not pulled; "
                              f"run `ollama pull {model}`)",
                    "model": None,
                }
        except requests.Timeout:
            return {"available": False, "text": fallback_text,
                    "source": "rule-based fallback (Ollama timed out)", "model": None}
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Ollama call failed: %s", exc)

        return {"available": False, "text": fallback_text,
                "source": "rule-based fallback (Ollama unavailable)", "model": None}

    # ------------------------------------------------------------------
    @staticmethod
    def _build_prompt(
        job_title: str, company: str, risk_level: str, risk_score: int,
        flags: List[Dict[str, Any]],
    ) -> str:
        flag_lines = "\n".join(
            f"- {flag.get('flag') or flag.get('title')} [{flag.get('severity')}]: "
            f"{flag.get('explanation', '')}"
            for flag in flags
        ) or "- none detected"

        return (
            "You are a cybersecurity analyst helping a job seeker understand an automated "
            "fraud-risk assessment. Write 3-4 plain-English sentences explaining the verdict, "
            "then exactly two concrete safety actions as bullet points.\n\n"
            "Constraints:\n"
            "- Do not change, question or restate a different risk score or verdict.\n"
            "- Do not invent facts about the employer.\n"
            "- Do not ask for or repeat personal data.\n"
            "- Be calm and direct; no alarmist language.\n\n"
            f"Job title: {job_title}\n"
            f"Company: {company or 'not stated'}\n"
            f"Verdict: {risk_level} (risk score {risk_score}/100)\n"
            f"Triggered checks:\n{flag_lines}\n"
        )

    @staticmethod
    def _sanitise(text: str) -> str:
        """
        Constrains model output: strips whitespace, collapses blank lines and caps length
        so a runaway generation cannot flood the UI.
        """
        cleaned = re.sub(r"\n{3,}", "\n\n", (text or "").strip())
        return cleaned[:1500]

    @staticmethod
    def _template_explanation(
        risk_level: str, risk_score: int, flags: List[Dict[str, Any]]
    ) -> str:
        """Deterministic narrative used whenever the LLM is unavailable."""
        if flags:
            top = flags[0]
            text = (
                f"This posting scored {risk_score}/100 and was classified {risk_level}. "
                f"The strongest signal is '{top.get('flag') or top.get('title')}': "
                f"{top.get('explanation', '')}"
            )
            if len(flags) > 1:
                others = "; ".join(
                    str(flag.get("flag") or flag.get("title")) for flag in flags[1:3]
                )
                text += f" Other findings: {others}."
        else:
            text = (
                f"This posting scored {risk_score}/100 and was classified {risk_level}. "
                "No heuristic red flags or strong fraud signals were detected."
            )
        return text + (
            " Regardless of this score, never pay a fee to secure a job and never share "
            "OTPs, banking credentials or identity documents before a signed written offer."
        )


_service: Optional[ExplanationService] = None


def get_explanation_service() -> ExplanationService:
    global _service
    if _service is None:
        _service = ExplanationService()
    return _service
