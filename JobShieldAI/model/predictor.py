"""
Predictor Module for JobShield AI

Loads the serialized TF-IDF vectorizer and calibrated Logistic Regression model and
generates a fraud probability for a job advertisement.

Robustness contract
-------------------
* If artifacts are missing or fail to load, ``is_ready`` is False and predictions
  return a neutral 0.5 probability flagged as ``is_ready: False`` so the risk engine
  knows to trust the heuristic engine instead of a phantom model.
* If artifacts were trained by a different scikit-learn version, loading may raise;
  that is caught, logged and degraded gracefully rather than crashing the API.
* Inference never raises for unusual input — empty, very long, or emoji-only text
  still returns a well-formed result.
"""

import logging
import os
from typing import Any, Dict, Optional

import joblib

logger = logging.getLogger(__name__)

DEFAULT_MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "saved_models"
)

NEUTRAL_RESULT: Dict[str, Any] = {
    "is_ready": False,
    "prediction_label": "Model Not Loaded",
    "fraud_probability": 0.5,
    "genuine_probability": 0.5,
    "fraud_score_pct": 50.0,
    "message": "Model artifacts not found. Run `python model/train_model.py`.",
}


class JobPredictor:
    def __init__(self, model_dir: Optional[str] = None):
        self.model_dir = model_dir or DEFAULT_MODEL_DIR
        self.vectorizer_path = os.path.join(self.model_dir, "tfidf_vectorizer.pkl")
        self.model_path = os.path.join(self.model_dir, "model.pkl")
        self.vectorizer = None
        self.model = None
        self.load_error: Optional[str] = None
        self._load_artifacts()

    # ------------------------------------------------------------------
    def _load_artifacts(self) -> None:
        """Loads vectorizer and model if available; records any failure reason."""
        if not (os.path.exists(self.vectorizer_path) and os.path.exists(self.model_path)):
            self.load_error = (
                f"Artifacts not found in '{self.model_dir}'. "
                "Run `python model/train_model.py` to generate them."
            )
            logger.warning(self.load_error)
            return

        try:
            self.vectorizer = joblib.load(self.vectorizer_path)
            self.model = joblib.load(self.model_path)
            self.load_error = None
        except Exception as exc:  # version mismatch, corrupt pickle, missing deps
            self.vectorizer = None
            self.model = None
            self.load_error = f"Failed to load model artifacts: {exc}"
            logger.error(self.load_error)

    @property
    def is_ready(self) -> bool:
        return self.vectorizer is not None and self.model is not None

    # ------------------------------------------------------------------
    def predict(self, text: str) -> Dict[str, Any]:
        """Runs inference and returns calibrated probabilities."""
        if not self.is_ready:
            return dict(NEUTRAL_RESULT, message=self.load_error or NEUTRAL_RESULT["message"])

        cleaned = (text or "").strip()
        if not cleaned:
            return {
                "is_ready": True,
                "prediction_label": "Genuine",
                "fraud_probability": 0.0,
                "genuine_probability": 1.0,
                "fraud_score_pct": 0.0,
                "message": "Empty text provided; no fraud signal.",
            }

        try:
            features = self.vectorizer.transform([cleaned])
            probabilities = self.model.predict_proba(features)[0]
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Inference failed: %s", exc)
            return dict(NEUTRAL_RESULT, message=f"Inference failed: {exc}")

        # Map by class label rather than assuming column order.
        classes = list(getattr(self.model, "classes_", [0, 1]))
        fraud_index = classes.index(1) if 1 in classes else 1
        fraud_prob = float(probabilities[fraud_index])
        genuine_prob = 1.0 - fraud_prob

        return {
            "is_ready": True,
            "prediction_label": "Fraudulent" if fraud_prob >= 0.50 else "Genuine",
            "fraud_probability": round(fraud_prob, 4),
            "genuine_probability": round(genuine_prob, 4),
            "fraud_score_pct": round(fraud_prob * 100, 2),
        }
