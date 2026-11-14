"""
Predictor Module for JobShield AI
Loads the serialized TF-IDF vectorizer and Logistic Regression model
to generate probability scores and classification predictions for new job advertisements.
"""

import os
import joblib
from typing import Dict, Any

class JobPredictor:
    def __init__(self, model_dir: str = "saved_models"):
        self.model_dir = model_dir
        self.vectorizer_path = os.path.join(model_dir, "tfidf_vectorizer.pkl")
        self.model_path = os.path.join(model_dir, "model.pkl")
        self.vectorizer = None
        self.model = None
        self._load_artifacts()

    def _load_artifacts(self):
        """Loads vectorizer and model if available."""
        if os.path.exists(self.vectorizer_path) and os.path.exists(self.model_path):
            self.vectorizer = joblib.load(self.vectorizer_path)
            self.model = joblib.load(self.model_path)
        else:
            self.vectorizer = None
            self.model = None

    @property
    def is_ready(self) -> bool:
        """Returns True if the ML model is trained and loaded."""
        return self.vectorizer is not None and self.model is not None

    def predict(self, text: str) -> Dict[str, Any]:
        """
        Runs inference on the provided text.
        Returns:
            dict containing:
                - is_ready (bool)
                - prediction_label ('Genuine' or 'Fraudulent')
                - fraud_probability (float, 0.0 to 1.0)
                - genuine_probability (float, 0.0 to 1.0)
        """
        if not self.is_ready:
            # Fallback if model hasn't been trained yet
            return {
                "is_ready": False,
                "prediction_label": "Model Not Loaded",
                "fraud_probability": 0.5,
                "genuine_probability": 0.5,
                "message": "Model artifacts not found. Please train the model."
            }

        cleaned_text = text.strip()
        if not cleaned_text:
            return {
                "is_ready": True,
                "prediction_label": "Genuine",
                "fraud_probability": 0.0,
                "genuine_probability": 1.0,
                "message": "Empty text provided."
            }

        # Transform text via TF-IDF
        features = self.vectorizer.transform([cleaned_text])
        probabilities = self.model.predict_proba(features)[0]
        
        # Binary classification: index 0 = Genuine, index 1 = Fraudulent
        genuine_prob = float(probabilities[0])
        fraud_prob = float(probabilities[1])
        
        prediction_label = "Fraudulent" if fraud_prob >= 0.50 else "Genuine"

        return {
            "is_ready": True,
            "prediction_label": prediction_label,
            "fraud_probability": round(fraud_prob, 4),
            "genuine_probability": round(genuine_prob, 4),
            "fraud_score_pct": round(fraud_prob * 100, 2)
        }

