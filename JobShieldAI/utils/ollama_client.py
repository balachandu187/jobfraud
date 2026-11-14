"""
Ollama Client for JobShield AI
Connects to local Ollama inference server (default: http://localhost:11434)
to enrich scam analysis with natural language explanations.
Provides seamless fallback if Ollama is not installed or unreachable.
"""

import requests
from typing import Dict, Any, List

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "llama3.2:latest"):
        self.base_url = base_url
        self.model_name = model_name
        self.timeout = 5.0  # short timeout to prevent UI lag on local machines

    def is_available(self) -> bool:
        """Checks if the local Ollama service is reachable."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=1.5)
            return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """Returns names of available local models."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=1.5)
            if resp.status_code == 200:
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass
        return []

    def generate_explanation(
        self,
        job_title: str,
        company: str,
        risk_score: int,
        risk_level: str,
        warnings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Requests an explanation from Ollama.
        Guarantees that Ollama output is purely supplementary and never alters scores.
        """
        if not self.is_available():
            return {
                "available": False,
                "text": "Ollama is not running locally. Showing standard rule-based explanations.",
                "source": "Predefined Template"
            }

        warning_list_str = "\n".join([f"- {w['title']}: {w['explanation']}" for w in warnings])
        if not warning_list_str:
            warning_list_str = "No severe red flags detected."

        prompt = (
            f"You are a cybersecurity expert analyzing a job posting.\n"
            f"Job Title: {job_title}\n"
            f"Company: {company or 'Not specified'}\n"
            f"Evaluated Risk Level: {risk_level} (Score: {risk_score}/100)\n"
            f"Detected Red Flags:\n{warning_list_str}\n\n"
            f"Provide a concise 3-4 sentence explanation for a job seeker on why this job is "
            f"classified as {risk_level} and 2 direct safety recommendations. Do not mention other scores."
        )

        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 150
                }
            }
            resp = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout)
            if resp.status_code == 200:
                result = resp.json().get("response", "").strip()
                if result:
                    return {
                        "available": True,
                        "text": result,
                        "source": f"Ollama ({self.model_name})"
                    }
        except Exception as e:
            # Graceful fallback on network timeout or model failure
            pass

        return {
            "available": False,
            "text": "Ollama query timed out or model unavailable. Displaying deterministic guidance.",
            "source": "Predefined Fallback"
        }

