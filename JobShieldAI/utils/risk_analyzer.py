"""
Risk Analyzer for JobShield AI
Combines Machine Learning prediction probability and Rule-Based warning scores
into an ensemble Risk Index (0 - 100) and risk tier classification.
"""

from typing import Dict, Any, List

class RiskAnalyzer:
    def __init__(self, ml_weight: float = 0.50, rule_weight: float = 0.50):
        """
        Weights for blending ML and Rule-based indicators.
        Default: 50% ML probability + 50% Rule score.
        If any CRITICAL rule triggers (like upfront fees or OTP theft),
        a risk floor is enforced to protect the applicant.
        """
        self.ml_weight = ml_weight
        self.rule_weight = rule_weight

    def calculate_risk(
        self,
        ml_result: Dict[str, Any],
        rule_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Produces final calibrated risk assessment.
        """
        fraud_prob = ml_result.get("fraud_probability", 0.0)
        ml_score = fraud_prob * 100.0  # 0 to 100
        
        rule_score = rule_result.get("rule_score", 0)  # 0 to 100
        warnings: List[Dict[str, Any]] = rule_result.get("warnings", [])

        # Base blended score
        combined_score = (ml_score * self.ml_weight) + (rule_score * self.rule_weight)

        # Safety override: If any CRITICAL severity warning is present, minimum risk is 75
        has_critical = any(w.get("severity") == "CRITICAL" for w in warnings)
        if has_critical and combined_score < 75:
            combined_score = 75.0

        # Cap score between 0 and 100
        final_score = int(round(max(0.0, min(100.0, combined_score))))

        # Determine risk classification tier
        if final_score < 35:
            risk_level = "Low Risk"
            verdict = "Likely Genuine"
            theme_color = "#10B981"  # Emerald green
            badge_icon = "shield-check"
        elif final_score < 66:
            risk_level = "Medium Risk"
            verdict = "Suspicious"
            theme_color = "#F59E0B"  # Amber orange
            badge_icon = "alert-triangle"
        else:
            risk_level = "High Risk"
            verdict = "Potentially Fraudulent"
            theme_color = "#EF4444"  # Crimson red
            badge_icon = "alert-octagon"

        return {
            "risk_score": final_score,
            "risk_level": risk_level,
            "verdict": verdict,
            "theme_color": theme_color,
            "badge_icon": badge_icon,
            "ml_score": round(ml_score, 1),
            "rule_score": rule_score,
            "ml_prediction": ml_result.get("prediction_label", "Unknown"),
            "warnings": warnings,
            "warning_count": len(warnings),
            "disclaimer": "This score is an automated security estimate and not definitive legal proof that an organization is fraudulent."
        }

