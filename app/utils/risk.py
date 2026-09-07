import re
from typing import List, Tuple, Dict

LEET_MAP = str.maketrans("0134578", "oieastb")

_SPACED_CHAR_RUN = re.compile(r"(?:\b\w)(?:\s+\w){2,}\b")


def _normalize_leetspeak(text: str) -> str:
    """Normalize common leetspeak substitutions before keyword matching."""
    return text.lower().translate(LEET_MAP)


def _normalize_spacing(text: str) -> str:
    """Ensure space after punctuation so collapse regex doesn't merge across commas."""
    text = re.sub(r"([,;.!?:])(\S)", r"\1 \2", text)
    text = _SPACED_CHAR_RUN.sub(lambda m: m.group().replace(" ", ""), text)
    return text


def _is_char_spaced(text: str) -> bool:
    """Detect if text has character-level spacing (evasion technique)."""
    words = text.split()
    if len(words) < 3:
        return False
    single_chars = sum(1 for w in words if len(w) == 1 and w.isalpha())
    return single_chars / len(words) > 0.4


def _fuzzy_phrase(pattern_words: list) -> re.Pattern:
    """Build regex that tolerates character-level spacing between words."""
    parts = []
    for i, word in enumerate(pattern_words):
        word_re = r"\s*".join(re.escape(c) for c in word)
        if i == 0:
            parts.append(word_re)
        else:
            parts.append(r"\s+" + word_re)
    return re.compile("".join(parts), re.IGNORECASE)


# Multi-word phrases: (display_name, weight, words_list)
_PHRASE_DEFS: List[Tuple[str, float, List[str]]] = [
    ("processing fee", 0.34, ["processing", "fee"]),
    ("registration fee", 0.30, ["registration", "fee"]),
    ("advance payment", 0.32, ["advance", "payment"]),
    ("send money", 0.28, ["send", "money"]),
    ("50000 per week", 0.28, ["50000", "per", "week"]),
    ("100000 per month", 0.27, ["100000", "per", "month"]),
    ("urgent hiring", 0.15, ["urgent", "hiring"]),
    ("job available", 0.08, ["job", "available"]),
    ("click here", 0.18, ["click", "here"]),
    ("limited seats", 0.16, ["limited", "seats"]),
]

# Compiled normal (word-boundary) and fuzzy patterns
_PHRASE_NORMAL: List[Tuple[str, float, re.Pattern]] = []
_PHRASE_FUZZY: List[Tuple[str, float, re.Pattern]] = []
for _name, _weight, _words in _PHRASE_DEFS:
    _normal_re = re.compile(r"\b" + r"\s+".join(re.escape(w) for w in _words) + r"\b")
    _PHRASE_NORMAL.append((_name, _weight, _normal_re))
    _PHRASE_FUZZY.append((_name, _weight, _fuzzy_phrase(_words)))

# Single-word patterns use simple substring matching.
_WORD_PATTERNS: Dict[str, float] = {
    "ganja": 0.25,
    "kutta": 0.25,
    "kamina": 0.25,
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
    """Heuristic risk scorer with leetspeak, spacing evasion, and ensemble support.

    Three-pass detection:
    1. Normal word-boundary matching on collapsed text
    2. Leetspeak normalization + re-check
    3. Fuzzy character-spacing matching on original text (for spacing evasion)

    Returns score, confidence, risk_level, flagged phrases with contributions,
    and a human-readable explanation.
    """
    original_text = text
    text = _normalize_spacing(text)
    lower_text = text.lower()
    leet_text = _normalize_leetspeak(text)
    char_spaced = _is_char_spaced(original_text)

    flagged: List[Dict[str, float]] = []
    seen: set = set()
    total_contribution = 0.0

    # Pass 1 & 2: normal + leetspeak matching on collapsed text
    for name, contribution, pattern in _PHRASE_NORMAL:
        if pattern.search(lower_text) or pattern.search(leet_text):
            if name not in seen:
                seen.add(name)
                c = round(contribution * 1.65, 3) if contribution >= 0.25 else contribution
                flagged.append({"phrase": name, "contribution": c})
                total_contribution += c

    # Pass 3: fuzzy matching for character-spaced evasion
    if char_spaced:
        for name, contribution, pattern in _PHRASE_FUZZY:
            if name not in seen and pattern.search(original_text):
                seen.add(name)
                c = round(contribution * 1.65, 3) if contribution >= 0.25 else contribution
                flagged.append({"phrase": name, "contribution": c})
                total_contribution += c

    # Single-word patterns (substring match on both variants)
    for word, contribution in _WORD_PATTERNS.items():
        if word in lower_text or word in leet_text:
            c = round(contribution * 1.65, 3) if contribution >= 0.25 else contribution
            flagged.append({"phrase": word, "contribution": c})
            total_contribution += c

    score = min(round(total_contribution, 2), 0.99)
    confidence = round(0.5 + 0.5 * score, 2)
    risk_level = _risk_level(score)
    explanation = _explanation(score, flagged)
    return score, confidence, risk_level, flagged, explanation
