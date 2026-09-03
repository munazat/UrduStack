import re
from typing import List, Tuple, Dict

# Heuristic scam/toxic keyword list for the skeleton.
# The real model should be a LoRA-fine-tuned XLM-RoBERTa on PURUTT.
HIGH_RISK_PATTERNS: Dict[str, float] = {
    "processing fee": 0.34,
    "registration fee": 0.30,
    "advance payment": 0.32,
    "send money": 0.28,
    "50000 per week": 0.28,
    "100000 per month": 0.27,
    "urgent hiring": 0.15,
    "job available": 0.08,
    "click here": 0.18,
    "limited seats": 0.16,
    "ganja": 0.25,
    "kutta": 0.25,
    "bhosri": 0.35,
    "chutiya": 0.35,
    "madarchod": 0.45,
    "benchod": 0.45,
}


def _risk_level(score: float) -> str:
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def _explanation(score: float, phrases: List[str]) -> str:
    if score >= 0.7:
        return f"High risk: detected {len(phrases)} strong indicator(s)."
    if score >= 0.4:
        return f"Medium risk: detected {len(phrases)} suspicious phrase(s)."
    return "Low risk: no strong indicators detected."


def compute_risk_score(text: str) -> Tuple[float, float, str, List[Dict[str, float]], str]:
    """Heuristic risk scorer stub.

    Returns score, confidence, risk_level, flagged phrases with contributions,
    and a human-readable explanation. Replace with a real fine-tuned
    transformer + temperature scaling once the model is trained.
    """
    lower_text = text.lower()
    flagged: List[Dict[str, float]] = []
    total_contribution = 0.0
    for phrase, contribution in HIGH_RISK_PATTERNS.items():
        if phrase in lower_text:
            flagged.append({"phrase": phrase, "contribution": contribution})
            total_contribution += contribution

    score = min(round(total_contribution, 2), 0.99)
    confidence = round(0.5 + 0.5 * score, 2)
    risk_level = _risk_level(score)
    explanation = _explanation(score, flagged)
    return score, confidence, risk_level, flagged, explanation
