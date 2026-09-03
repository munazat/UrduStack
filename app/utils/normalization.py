import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

from app.utils.roman_urdu_map import ROMAN_TO_URDU

_FREQ_MAP_PATH = Path("data/processed/roman_urdu_freq.json")


def _load_frequency_map() -> Dict[str, str]:
    if _FREQ_MAP_PATH.exists():
        with _FREQ_MAP_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# Prefer dataset-derived frequency map, fall back to hand-curated starter map.
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


def normalize_text(text: str) -> str:
    """Rule-based code-switch-aware normalization.

    Replaces known Roman-Urdu tokens with Urdu script and leaves Urdu-script
    tokens and other tokens untouched. Uses a dataset-derived frequency map
    when available (run `scripts/build_normalizer_map.py` on Roman-Urdu-Parl),
    otherwise falls back to a hand-curated starter map.
    """
    tokens = text.split()
    normalized_tokens: List[str] = []
    for token in tokens:
        mapping = _lookup(token)
        normalized_tokens.append(mapping if mapping else token)
    return " ".join(normalized_tokens)


def normalize_with_segments(text: str) -> Tuple[str, float, List[Dict]]:
    tokens = text.split()
    segments: List[Dict] = []
    normalized_tokens: List[str] = []
    confident = 0
    for token in tokens:
        script = detect_script(token)
        mapping = _lookup(token)
        if mapping:
            normalized_tokens.append(mapping)
            confident += 1
        else:
            normalized_tokens.append(token)
        segments.append(
            {
                "original": token,
                "normalized": mapping if mapping else token,
                "detected_script": script,
            }
        )
    confidence = round(confident / max(len(tokens), 1), 2)
    return " ".join(normalized_tokens), confidence, segments
