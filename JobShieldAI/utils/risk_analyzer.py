"""
Risk Analyzer for JobShield AI

Blends the calibrated ML fraud probability with the deterministic heuristic score into
a single 0-100 Risk Index, then applies safety floors so severe findings can never be
averaged away by a confident classifier.

Scoring contract
----------------
    combined = ml_score * ml_weight + rule_score * rule_weight
    floors   = CRITICAL warning -> >= 75   (High Risk, never below)
               HIGH warning     -> >= 45   (at least Medium Risk)
               2+ MEDIUM        -> >= 45   (at least Medium Risk)
    final    = clamp(round(max(combined, floor)), 0, 100)

Tiers: 0-34 Low Risk | 35-65 Medium Risk | 66-100 High Risk
"""

from typing import Any, Dict, List

CRITICAL_FLOOR = 75
ELEVATED_FLOOR = 45

_SEVERITY_ORDER = ("CRITICAL", "HIGH", "MEDIUM", "LOW")


class RiskAnalyzer:
    def __init__(self, ml_weight: float = 0.50, rule_weight: float = 0.50):
        if ml_weight < 0 or rule_weight < 0:
            raise ValueError("Weights must be non-negative.")
        total = ml_weight + rule_weight
        # Normalise so callers can pass any positive ratio, e.g. (2, 1).
        self.ml_weight = ml_weight / total
        self.rule_weight = rule_weight / total

    def calculate_risk(
        self,
        ml_result: Dict[str, Any],
        rule_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Produces the final calibrated risk assessment."""
        fraud_prob = float(ml_result.get("fraud_probability", 0.0) or 0.0)
        ml_score = max(0.0, min(1.0, fraud_prob)) * 100.0

        rule_score = float(rule_result.get("rule_score", 0) or 0)
        warnings: List[Dict[str, Any]] = list(rule_result.get("warnings", []))

        combined_score = (ml_score * self.ml_weight) + (rule_score * self.rule_weight)

        severity_counts = {severity: 0 for severity in _SEVERITY_ORDER}
        for warning in warnings:
            severity = str(warning.get("severity", "")).upper()
            if severity in severity_counts:
                severity_counts[severity] += 1

        applied_floors: List[str] = []
        floor = 0.0
        if severity_counts["CRITICAL"]:
            floor = max(floor, CRITICAL_FLOOR)
            applied_floors.append(f"CRITICAL warning -> floor {CRITICAL_FLOOR}")
        if severity_counts["HIGH"]:
            floor = max(floor, ELEVATED_FLOOR)
            applied_floors.append(f"HIGH warning -> floor {ELEVATED_FLOOR}")
        if severity_counts["MEDIUM"] >= 2:
            floor = max(floor, ELEVATED_FLOOR)
            applied_floors.append(f"{severity_counts['MEDIUM']} MEDIUM warnings -> floor {ELEVATED_FLOOR}")

        final_score = int(round(max(0.0, min(100.0, max(combined_score, floor)))))

        if final_score < 35:
            risk_level, verdict = "Low Risk", "Likely Genuine"
            theme_color, badge_icon = "#10B981", "shield-check"
        elif final_score < 66:
            risk_level, verdict = "Medium Risk", "Suspicious"
            theme_color, badge_icon = "#F59E0B", "alert-triangle"
        else:
            risk_level, verdict = "High Risk", "Potentially Fraudulent"
            theme_color, badge_icon = "#EF4444", "alert-octagon"

        # Distance of the blended score from the 50/50 decision boundary, expressed 0-1.
        confidence = round(abs(combined_score - 50.0) / 50.0, 3)

        return {
            "risk_score": final_score,
            "risk_level": risk_level,
            "verdict": verdict,
            "theme_color": theme_color,
            "badge_icon": badge_icon,
            "ml_score": round(ml_score, 1),
            "rule_score": int(round(rule_score)),
            "blended_score": round(combined_score, 1),
            "enforced_floor": int(floor),
            "floor_reasons": applied_floors,
            "ml_prediction": ml_result.get("prediction_label", "Unknown"),
            "ml_ready": bool(ml_result.get("is_ready", False)),
            "confidence": confidence,
            "severity_counts": severity_counts,
            "warnings": warnings,
            "warning_count": len(warnings),
            "disclaimer": (
                "This score is an automated security estimate, not definitive legal proof "
                "that an organisation is fraudulent. Always verify independently."
            ),
        }
