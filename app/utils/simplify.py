"""Lexical simplification for Urdu text.

Replaces complex or formal Urdu words with simpler, more commonly used
alternatives. Useful for making formal Urdu text more accessible.
"""

from typing import Dict, List, Tuple

COMPLEX_TO_SIMPLE: Dict[str, str] = {
    "استعمال": "use",
    "ضروری": "اہم",
    "معلومات": "خبر",
    "تعلیم": "پڑھائی",
    "صحت": "تندرستی",
    "معاشرہ": "سماج",
    "اقتصادیات": "معاشیات",
    "سیاست": "راجنیتی",
    "حکومت": "سرکار",
    "انتظامیہ": "انتظام",
    "ترقی": "بہتری",
    "مشکل": "کٹھن",
    "آسان": "سہل",
    "مناسب": "ٹھیک",
    "ضرورت": "لوڑ",
    "کوشش": "جتتن",
    "محنت": "مشقت",
    "ذمہ داری": "فریضہ",
    "موقع": "موقعہ",
    "فائدہ": "لابھ",
    "نقصان": "گھاٹا",
    "تجارت": "کاروبار",
    "صنعت": "کارخانہ",
    "زراعت": "کھیتی",
    "مواصلات": "رابطہ",
    "ٹیکنالوجی": "ٹیکنالوجی",
}

_URDU_SCRIPT_CHARS = set("؀؁؂؃؄؅؆؇؈؉؊؋،؍؎؏ؘؙؚؐؑؒؓؔؕؖؗ؞۔ؠءآأؤإئابةتثج؍؎؏ؘؙؚؐؑؒؓؔؕؖؗ؞")


def _is_urdu_script(text: str) -> bool:
    import re
    return bool(re.search(r"[\u0600-\u06FF]", text))


def simplify(text: str) -> Tuple[str, List[Dict[str, str]]]:
    """Simplify complex Urdu words in text.

    Returns:
        (simplified_text, list_of_changes)
        Each change dict has: original, simplified
    """
    if not text or not text.strip():
        return text, []

    if not _is_urdu_script(text):
        return text, []

    tokens = text.split()
    simplified_tokens = []
    changes = []

    for token in tokens:
        stripped = token.strip(".,!?؛،")
        lower = stripped.lower() if stripped else ""

        if lower in COMPLEX_TO_SIMPLE:
            replacement = COMPLEX_TO_SIMPLE[lower]
            leading = token[: len(token) - len(token.lstrip(".,!?؛،"))]
            trailing = token[len(token.rstrip(".,!?؛،")) :]
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
    if not text or not _is_urdu_script(text):
        return {"total_words": 0, "complex_words": 0, "complexity_ratio": 0.0}

    tokens = text.split()
    complex_count = sum(
        1 for t in tokens if t.strip(".,!?؛،").lower() in COMPLEX_TO_SIMPLE
    )
    return {
        "total_words": len(tokens),
        "complex_words": complex_count,
        "complexity_ratio": round(complex_count / max(len(tokens), 1), 3),
    }
