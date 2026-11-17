"""
Risk analysis engine.

Combines the machine-learning probability with the rule-based score into a single
0-100 Risk Score, then applies safety floors so severe findings cannot be averaged
away by a confident classifier.

Scoring method (fully documented, and configurable via backend/config.py)
-----------------------------------------------------------------------
1. **Engine scores**
   * `ml_score`   = ML fraud probability × 100        (0-100)
   * `rule_score` = sum of fired rule weights, clamped (0-100)

2. **Weighted blend**
   `blended = (ml_score × ml_weight) + (rule_score × rule_weight)`
   Defaults: 0.5 / 0.5.

3. **Safety floors** (applied after the blend, never before)
   * any CRITICAL flag        -> score = max(score, 75)
   * any HIGH flag            -> score = max(score, 45)
   * two or more MEDIUM flags -> score = max(score, 45)
   Floors exist because a missing OTP request is a catastrophic false negative, while
   an over-cautious flag only costs the user a few minutes of verification.

4. **Classification**
   * 0-34  -> "Low Risk"
   * 35-65 -> "Medium Risk"
   * 66-100 -> "High Risk"
   (Boundaries come from config: `low_risk_max`, `high_risk_min`.)

5. **Verdict wording** — deliberately hedged. The model cannot prove fraud, so the
   output says "Possibly Fraudulent", never "definitely fraudulent".
"""

from __future__ import annotations

from typing import Any, Dict, List

from backend.config import settings

LOW_RISK = "Low Risk"
MEDIUM_RISK = "Medium Risk"
HIGH_RISK = "High Risk"

VERDICTS = {
    LOW_RISK: "Likely Genuine",
    MEDIUM_RISK: "Suspicious",
    HIGH_RISK: "Possibly Fraudulent",
}

THEME_COLORS = {LOW_RISK: "#10B981", MEDIUM_RISK: "#F59E0B", HIGH_RISK: "#EF4444"}
BADGE_ICONS = {LOW_RISK: "shield-check", MEDIUM_RISK: "alert-triangle", HIGH_RISK: "alert-octagon"}


class RiskAnalyzer:
    """Blends ML and rule output into a final, explainable risk assessment."""

    def __init__(
        self,
        ml_weight: float | None = None,
        rule_weight: float | None = None,
        critical_floor: int | None = None,
        elevated_floor: int | None = None,
        low_risk_max: int | None = None,
        high_risk_min: int | None = None,
    ) -> None:
        ml_weight = settings.ml_weight if ml_weight is None else ml_weight
        rule_weight = settings.rule_weight if rule_weight is None else rule_weight
        if ml_weight < 0 or rule_weight < 0:
            raise ValueError("weights must be non-negative")
        total = ml_weight + rule_weight
        if total <= 0:
            raise ValueError("at least one weight must be positive")
        # Normalise so any positive ratio works, e.g. (2, 1).
        self.ml_weight = ml_weight / total
        self.rule_weight = rule_weight / total

        self.critical_floor = settings.critical_floor if critical_floor is None else critical_floor
        self.elevated_floor = settings.elevated_floor if elevated_floor is None else elevated_floor
        self.low_risk_max = settings.low_risk_max if low_risk_max is None else low_risk_max
        self.high_risk_min = settings.high_risk_min if high_risk_min is None else high_risk_min

    # ------------------------------------------------------------------
    def classify(self, score: int) -> str:
        if score <= self.low_risk_max:
            return LOW_RISK
        if score >= self.high_risk_min:
            return HIGH_RISK
        return MEDIUM_RISK

    # ------------------------------------------------------------------
    def analyze(
        self,
        ml_result: Dict[str, Any],
        rule_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Args:
            ml_result: must contain `fraud_probability`, `prediction_label`, `is_ready`.
            rule_result: must contain `flags`, `rule_score`.

        Returns a dict describing the final score and exactly how it was reached.
        """
        probability = float(ml_result.get("fraud_probability") or 0.0)
        probability = max(0.0, min(1.0, probability))
        ml_score = probability * 100.0

        rule_score = float(rule_result.get("rule_score") or 0.0)
        rule_score = max(0.0, min(100.0, rule_score))

        flags: List[Dict[str, Any]] = list(rule_result.get("flags") or [])

        blended = (ml_score * self.ml_weight) + (rule_score * self.rule_weight)

        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for flag in flags:
            severity = str(flag.get("severity", "")).upper()
            if severity in severity_counts:
                severity_counts[severity] += 1

        floor = 0
        floor_reasons: List[str] = []
        if severity_counts["CRITICAL"]:
            floor = max(floor, self.critical_floor)
            floor_reasons.append(
                f"CRITICAL flag present -> minimum score {self.critical_floor}"
            )
        if severity_counts["HIGH"]:
            floor = max(floor, self.elevated_floor)
            floor_reasons.append(
                f"HIGH flag present -> minimum score {self.elevated_floor}"
            )
        if severity_counts["MEDIUM"] >= 2:
            floor = max(floor, self.elevated_floor)
            floor_reasons.append(
                f"{severity_counts['MEDIUM']} MEDIUM flags -> minimum score {self.elevated_floor}"
            )

        final_score = int(round(max(0.0, min(100.0, max(blended, float(floor))))))
        risk_level = self.classify(final_score)

        breakdown = {
            "ml_score": round(ml_score, 1),
            "rule_score": int(round(rule_score)),
            "ml_weight": self.ml_weight,
            "rule_weight": self.rule_weight,
            "blended_score": round(blended, 1),
            "enforced_floor": floor,
            "floor_reasons": floor_reasons,
            "final_score": final_score,
            "severity_counts": severity_counts,
            "formula": (
                f"score = ({round(ml_score, 1)} x {self.ml_weight}) + "
                f"({int(round(rule_score))} x {self.rule_weight}) = {round(blended, 1)}"
                + (f"; raised to floor {floor}" if floor > blended else "")
            ),
        }

        return {
            "risk_score": final_score,
            "risk_level": risk_level,
            "prediction": VERDICTS[risk_level],
            "verdict": VERDICTS[risk_level],
            "theme_color": THEME_COLORS[risk_level],
            "badge_icon": BADGE_ICONS[risk_level],
            "ml_prediction": ml_result.get("prediction_label", "Unknown"),
            "ml_probability": round(probability, 4),
            "ml_ready": bool(ml_result.get("is_ready", False)),
            "ml_score": round(ml_score, 1),
            "rule_score": int(round(rule_score)),
            "warning_count": len(flags),
            "flags": flags,
            "warnings": flags,          # alias kept for the existing UI
            "severity_counts": severity_counts,
            "score_breakdown": breakdown,
            "confidence": round(abs(blended - 50.0) / 50.0, 3),
            "explanation": self._summarise(risk_level, final_score, flags, breakdown, ml_result),
            "disclaimer": (
                "This score is an automated risk estimate produced by a statistical model and "
                "documented heuristics. It is not proof that the employer is fraudulent — "
                "always verify independently before acting."
            ),
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _summarise(
        risk_level: str,
        score: int,
        flags: List[Dict[str, Any]],
        breakdown: Dict[str, Any],
        ml_result: Dict[str, Any],
    ) -> str:
        """One-paragraph plain-language justification of the final score."""
        parts = [
            f"Scored {score}/100, classified {risk_level}. "
            f"The machine-learning model returned a {breakdown['ml_score']}% fraud probability "
            f"and the rule engine contributed {breakdown['rule_score']}/100."
        ]
        if breakdown["enforced_floor"]:
            parts.append(
                " A safety floor was applied: "
                + "; ".join(breakdown["floor_reasons"])
                + "."
            )
        if flags:
            names = ", ".join(flag.get("flag", flag.get("id", "")) for flag in flags[:4])
            parts.append(f" Triggered checks: {names}.")
        else:
            parts.append(" No heuristic red flags were detected.")
        if not ml_result.get("is_ready", False):
            parts.append(
                " Note: the ML model was unavailable, so this score is based on the rule "
                "engine alone."
            )
        return "".join(parts)
