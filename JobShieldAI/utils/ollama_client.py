"""
Ollama Client for JobShield AI

Connects to a local Ollama inference server (default http://localhost:11434) to add a
plain-language explanation on top of the deterministic verdict.

Hard guarantees
---------------
* Ollama is strictly *explanatory*. It never influences the risk score, verdict, or
  the warning list — those come from the ML + rule engines only.
* Every call degrades gracefully: if the server is down, slow, missing the model, or
  returns junk, a deterministic template is returned instead and the UI keeps working.

Configuration (environment variables)
-------------------------------------
    JOBSHIELD_OLLAMA_URL     default http://localhost:11434
    JOBSHIELD_OLLAMA_MODEL   default llama3.2:latest
    JOBSHIELD_OLLAMA_TIMEOUT default 60 (seconds, generation call)
"""

import os
from typing import Any, Dict, List

import requests

DEFAULT_BASE_URL = os.environ.get("JOBSHIELD_OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("JOBSHIELD_OLLAMA_MODEL", "llama3.2:latest")
HEALTH_TIMEOUT = 1.5
GENERATE_TIMEOUT = float(os.environ.get("JOBSHIELD_OLLAMA_TIMEOUT", "60"))


def _fallback(risk_level: str, risk_score: int, warnings: List[Dict[str, Any]], reason: str) -> Dict[str, Any]:
    """Deterministic, always-available explanation used when the LLM is unavailable."""
    if warnings:
        top = warnings[0]
        summary = (
            f"This posting scores {risk_score}/100 and is classified {risk_level}. "
            f"The most severe signal is '{top.get('title', 'a red flag')}': {top.get('explanation', '')}"
        )
        if len(warnings) > 1:
            others = ", ".join(w.get("title", "") for w in warnings[1:3] if w.get("title"))
            if others:
                summary += f" Additional findings: {others}."
    else:
        summary = (
            f"This posting scores {risk_score}/100 and is classified {risk_level}. "
            "No heuristic red flags were triggered, but always confirm the employer independently."
        )
    summary += (
        " Safety advice: never pay any fee to secure a job, and never share OTPs, "
        "net-banking credentials or identity documents before a signed written offer."
    )
    return {"available": False, "text": summary, "source": reason, "model": None}


class OllamaClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, model_name: str = DEFAULT_MODEL):
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.model_name = model_name or DEFAULT_MODEL
        self.timeout = GENERATE_TIMEOUT

    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        """Checks whether the local Ollama service is reachable."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=HEALTH_TIMEOUT)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def list_models(self) -> List[str]:
        """Returns the names of locally installed Ollama models."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=HEALTH_TIMEOUT)
            if response.status_code == 200:
                return [model.get("name", "") for model in response.json().get("models", []) if model.get("name")]
        except (requests.RequestException, ValueError):
            pass
        return []

    # ------------------------------------------------------------------
    def generate_explanation(
        self,
        job_title: str,
        company: str,
        risk_score: int,
        risk_level: str,
        warnings: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Requests a narrative explanation from Ollama with a guaranteed fallback."""
        if not self.is_available():
            return _fallback(risk_level, risk_score, warnings, "Predefined Template (Ollama offline)")

        installed = self.list_models()
        model = self.model_name
        if installed and model not in installed:
            # Prefer an installed model over failing on the configured one.
            model = installed[0]

        warning_text = "\n".join(
            f"- {w.get('title', 'Red flag')} [{w.get('severity', 'UNKNOWN')}]: {w.get('explanation', '')}"
            for w in warnings
        ) or "No heuristic red flags were detected."

        prompt = (
            "You are a cybersecurity analyst advising a job seeker. "
            "Write 3-4 plain-English sentences explaining the verdict below, then exactly two "
            "concrete safety actions as bullet points. Be direct and calm. Do not invent facts, "
            "do not mention any score other than the one given, and do not change the verdict.\n\n"
            f"Job title: {job_title}\n"
            f"Company: {company or 'Not specified'}\n"
            f"Verdict: {risk_level} (risk score {risk_score}/100)\n"
            f"Detected signals:\n{warning_text}\n"
        )

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
                text = (response.json().get("response") or "").strip()
                if text:
                    return {
                        "available": True,
                        "text": text,
                        "source": f"Ollama ({model})",
                        "model": model,
                    }
            elif response.status_code == 404:
                return _fallback(
                    risk_level, risk_score, warnings,
                    f"Predefined Template (model '{model}' not pulled: run `ollama pull {model}`)",
                )
        except requests.Timeout:
            return _fallback(risk_level, risk_score, warnings, "Predefined Template (Ollama timed out)")
        except (requests.RequestException, ValueError):
            pass

        return _fallback(risk_level, risk_score, warnings, "Predefined Template (Ollama unavailable)")
