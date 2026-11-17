"""
Machine-learning service.

Loads the TF-IDF vectorizer and calibrated Logistic Regression model **once** at startup
and reuses them for every request — models are never retrained per request.

If artifacts are missing or unloadable, the service reports `is_ready = False` and
returns neutral probabilities. It never fabricates a prediction: the risk analyzer is
told the model is unavailable and the response says so explicitly.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import joblib

from backend.config import settings

logger = logging.getLogger(__name__)

NEUTRAL: Dict[str, Any] = {
    "is_ready": False,
    "prediction_label": "Model Unavailable",
    "fraud_probability": 0.5,
    "genuine_probability": 0.5,
    "fraud_score_pct": 50.0,
}


class MLService:
    """Wraps the persisted sklearn artifacts."""

    def __init__(self, model_dir: Optional[Path] = None) -> None:
        self.model_dir = Path(model_dir or settings.model_dir)
        self.vectorizer: Any = None
        self.model: Any = None
        self.load_error: Optional[str] = None
        self.metrics: Dict[str, Any] = {}
        self._load()

    # ------------------------------------------------------------------
    def _load(self) -> None:
        vectorizer_path = self.model_dir / "tfidf_vectorizer.pkl"
        model_path = self.model_dir / "model.pkl"
        metrics_path = self.model_dir / "model_metrics.pkl"

        if not vectorizer_path.exists() or not model_path.exists():
            self.load_error = (
                f"Model artifacts not found in '{self.model_dir}'. "
                "Run `python -m backend.ml.train_model` to create them."
            )
            logger.warning(self.load_error)
            return

        try:
            self.vectorizer = joblib.load(vectorizer_path)
            self.model = joblib.load(model_path)
            if metrics_path.exists():
                self.metrics = joblib.load(metrics_path) or {}
            self.load_error = None
            logger.info(
                "ML artifacts loaded (vocabulary=%s)",
                getattr(self.vectorizer, "vocabulary_", {}).__len__(),
            )
        except Exception as exc:  # corrupt pickle, sklearn version mismatch, ...
            self.vectorizer = None
            self.model = None
            self.load_error = f"Failed to load model artifacts: {exc}"
            logger.error(self.load_error)

    # ------------------------------------------------------------------
    @property
    def is_ready(self) -> bool:
        return self.vectorizer is not None and self.model is not None

    def predict(self, text: str) -> Dict[str, Any]:
        """Returns a calibrated fraud probability for the given text."""
        if not self.is_ready:
            return dict(NEUTRAL, message=self.load_error or "Model not loaded.")

        cleaned = (text or "").strip()
        if not cleaned:
            return {
                "is_ready": True,
                "prediction_label": "Genuine",
                "fraud_probability": 0.0,
                "genuine_probability": 1.0,
                "fraud_score_pct": 0.0,
                "message": "Empty text; no fraud signal.",
            }

        try:
            features = self.vectorizer.transform([cleaned])
            probabilities = self.model.predict_proba(features)[0]
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Inference failed: %s", exc)
            return dict(NEUTRAL, message=f"Inference failed: {exc}")

        # Map by class label rather than relying on column order.
        classes = list(getattr(self.model, "classes_", [0, 1]))
        fraud_index = classes.index(1) if 1 in classes else 1
        fraud_probability = float(probabilities[fraud_index])

        return {
            "is_ready": True,
            "prediction_label": "Fraudulent" if fraud_probability >= 0.5 else "Genuine",
            "fraud_probability": round(fraud_probability, 4),
            "genuine_probability": round(1.0 - fraud_probability, 4),
            "fraud_score_pct": round(fraud_probability * 100, 2),
            "model": self.metrics.get("algorithm", "TF-IDF + Logistic Regression"),
        }

    # ------------------------------------------------------------------
    def info(self) -> Dict[str, Any]:
        """Model metadata for /api/health and /api/model."""
        return {
            "ready": self.is_ready,
            "model_dir": str(self.model_dir),
            "error": self.load_error,
            "metrics": self.metrics.get("metrics", {}),
            "trained_at": self.metrics.get("trained_at"),
            "dataset_rows": self.metrics.get("dataset_rows"),
            "algorithm": self.metrics.get("algorithm", "TF-IDF + Logistic Regression"),
        }
