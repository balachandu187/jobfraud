"""
Explanation and Safety Advisory Module for JobShield AI
Generates actionable recommendations, verification checklists, and danger indicators.
"""

from typing import List, Dict, Any

def get_safety_recommendations(risk_level: str, warnings: List[Dict[str, Any]]) -> List[str]:
    """Generates tailored safety advice based on detected risk patterns."""
    recommendations = []
    
    # Universal check
    if risk_level == "Low Risk":
        recommendations.append("Verify the opening directly on the employer's official careers portal or verified LinkedIn page.")
        recommendations.append("Ensure official communications come from authenticated corporate email domains.")
        recommendations.append("Never share bank credentials or government identity scans prior to a verified written job offer.")
        return recommendations

    # Specific warnings advisory
    warning_ids = {w["id"] for w in warnings}

    if "UPFRONT_FEE" in warning_ids:
        recommendations.append("STOP IMMEDIATELY: Under no circumstance transfer funds, security deposits, or purchase software licenses for a job offer.")
    
    if "SENSITIVE_DATA_THEFT" in warning_ids:
        recommendations.append("PROTECT FINANCIAL CREDENTIALS: Never share OTPs, net banking passwords, or signed cancelled cheques.")

    if "GUARANTEED_NO_INTERVIEW" in warning_ids:
        recommendations.append("EXAMINE HIRING PROTOCOL: Genuine enterprises never extend employment offers without structured interviews or skill evaluations.")

    if "SUSPICIOUS_CHANNELS" in warning_ids:
        recommendations.append("REFUSE UNTRACKED CHANNELS: Insist on communicating via corporate email or scheduled Google Meet/Teams calls rather than Telegram or WhatsApp.")

    if "PERSONAL_EMAIL_DOMAIN" in warning_ids:
        recommendations.append("VERIFY RECRUITER IDENTITY: Look up the recruiter on LinkedIn and check if their email matches the official company domain.")

    if "MONEY_MULE_SCHEME" in warning_ids:
        recommendations.append("LEGAL RISK: Processing third-party funds or mystery checks through personal bank accounts is a serious criminal offense.")

    if not recommendations:
        recommendations.append("Conduct an independent web search for '[Company Name] fake job scam' to view recent applicant reports.")
        recommendations.append("Do not click external shortened links (bit.ly, tinyurl) sent by unknown contacts.")

    return recommendations

