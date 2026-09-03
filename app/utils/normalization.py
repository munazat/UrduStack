import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

from app.utils.roman_urdu_map import ROMAN_TO_URDU
from app.utils.transliterate import transliterate

_FREQ_MAP_PATH = Path("data/processed/roman_urdu_freq.json")


def _load_frequency_map() -> Dict[str, str]:
    if _FREQ_MAP_PATH.exists():
        with _FREQ_MAP_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


_FREQUENCY_MAP = _load_frequency_map()


def _lookup(token: str) -> str | None:
    lower = token.lower().strip(".,!?؛،")
    return _FREQUENCY_MAP.get(lower) or ROMAN_TO_URDU.get(lower)


def detect_script(token: str) -> str:
    if re.search(r"[\u0600-\u06FF]", token):
        return "urdu_script"
    if re.search(r"[a-zA-Z]", token):
        return "roman_urdu"
    return "other"


_ENGLISH_SIGNALS = re.compile(
    r"^(https?://|www\.|\d+$)"
    r"|ing$|tion$|ment$|ness$|able$|ous$|ive$|ful$|less$|ized?$"
)


def _normalize_token(token: str) -> str:
    """Dictionary lookup first, then phonetic transliteration for Roman Urdu."""
    stripped = token.strip(".,!?؛،")
    if not stripped:
        return token
    script = detect_script(stripped)
    if script == "urdu_script":
        return token
    if script != "roman_urdu":
        return token
    if _ENGLISH_SIGNALS.match(stripped.lower()):
        return token
    mapping = _lookup(stripped)
    if mapping:
        leading = token[: len(token) - len(token.lstrip(".,!?؛،"))]
        trailing = token[len(token.rstrip(".,!?؛،")) :]
        return f"{leading}{mapping}{trailing}"
    return transliterate(token)


def normalize_text(text: str) -> str:
    """Code-switch-aware normalization.

    Dictionary matches get exact Urdu script. Unknown Roman-Urdu words get
    phonetically transliterated so the output is always in Urdu script.
    Urdu-script tokens and non-Urdu tokens (URLs, numbers, English) pass
    through unchanged.
    """
    return " ".join(_normalize_token(t) for t in text.split())


def normalize_with_segments(text: str) -> Tuple[str, float, List[Dict]]:
    tokens = text.split()
    segments: List[Dict] = []
    normalized_tokens: List[str] = []
    matched = 0
    for token in tokens:
        script = detect_script(token)
        normalized = _normalize_token(token)
        if normalized != token:
            matched += 1
        normalized_tokens.append(normalized)
        segments.append(
            {
                "original": token,
                "normalized": normalized,
                "detected_script": script,
            }
        )
    confidence = round(matched / max(len(tokens), 1), 2)
    return " ".join(normalized_tokens), confidence, segments
