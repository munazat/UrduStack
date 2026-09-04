from __future__ import annotations

import re
from typing import Dict, List, Tuple

COMPLEX_TO_SIMPLE: Dict[str, str] = {
    "ضروری": "اہم",
    "معلومات": "خبر",
    "تعلیم": "پڑھائی",
    "صحت": "تندرستی",
    "حکومت": "سرکار",
    "انتظامیہ": "انتظام",
    "ترقی": "بہتری",
    "مناسب": "ٹھیک",
    "ضرورت": "لوڑ",
    "محنت": "مشقت",
    "تجارت": "کاروبار",
    "صنعت": "کارخانہ",
    "مواصلات": "رابطہ",
    "اقتصادیات": "معاشیات",
    "معاشرہ": "سماج",
    "زراعت": "کھیتی",
    "آزادی": "چھوٹ",
    "خوشحالی": "خوشی",
    "ذمہ داری": "فریضہ",
}


def _is_urdu_script(text: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF]", text))


def _maybe_normalize(text: str) -> str:
    """Convert Roman Urdu to Urdu script so simplify can work on both."""
    if _is_urdu_script(text):
        return text
    try:
        from app.utils.normalization import normalize_text

        return normalize_text(text)
    except ImportError:
        return text


def simplify(text: str) -> Tuple[str, List[Dict[str, str]]]:
    """Simplify complex Urdu words in text.

    Works on both Urdu-script and Roman Urdu input (Roman Urdu is
    normalized first). Multi-word phrases are matched before single words.

    Returns:
        (simplified_text, list_of_changes)
        Each change dict has: original, simplified
    """
    if not text or not text.strip():
        return text, []

    working = _maybe_normalize(text)
    if not _is_urdu_script(working):
        return text, []

    changes: List[Dict[str, str]] = []

    multi_word = sorted(
        [(k, v) for k, v in COMPLEX_TO_SIMPLE.items() if " " in k],
        key=lambda x: -len(x[0]),
    )
    for phrase, replacement in multi_word:
        if phrase in working:
            working = working.replace(phrase, replacement)
            changes.append({"original": phrase, "simplified": replacement})

    tokens = working.split()
    simplified_tokens: List[str] = []

    for token in tokens:
        stripped = token.strip(".,!?؛،")
        lower = stripped.lower() if stripped else ""

        if lower in COMPLEX_TO_SIMPLE:
            replacement = COMPLEX_TO_SIMPLE[lower]
            idx = token.find(stripped) if stripped else 0
            leading = token[:idx]
            trailing = token[idx + len(stripped):]
            simplified_tokens.append(f"{leading}{replacement}{trailing}")
            changes.append({"original": stripped, "simplified": replacement})
        else:
            simplified_tokens.append(token)

    return " ".join(simplified_tokens), changes


def get_vocabulary_level(text: str) -> Dict[str, int | float]:
    """Estimate vocabulary complexity of Urdu text.

    Returns:
        total_words: total word count
        complex_words: number of complex words found
        complexity_ratio: fraction of complex words (0-1)
    """
    working = _maybe_normalize(text) if text else ""
    if not working or not _is_urdu_script(working):
        return {"total_words": 0, "complex_words": 0, "complexity_ratio": 0.0}

    tokens = working.split()
    complex_count = sum(
        1 for t in tokens if t.strip(".,!?؛،").lower() in COMPLEX_TO_SIMPLE
    )
    return {
        "total_words": len(tokens),
        "complex_words": complex_count,
        "complexity_ratio": round(complex_count / max(len(tokens), 1), 3),
    }
