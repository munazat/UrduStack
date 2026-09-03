import re
from typing import List, Dict, Tuple

# Minimal starter mapping from common Roman-Urdu spellings to Urdu script.
# Replace or augment this with a frequency table derived from Roman-Urdu-Parl.
ROMAN_TO_URDU: Dict[str, str] = {
    "yar": "یار",
    "bhai": "بھائی",
    "bro": "بھائی",
    "mujhe": "مجھے",
    "mujhay": "مجھے",
    "pareshan": "پریشان",
    "mat": "مت",
    "karo": "کرو",
    "kro": "کرو",
    "nahi": "نہیں",
    "nai": "نہیں",
    "han": "ہاں",
    "haan": "ہاں",
    "kaisa": "کیسا",
    "kesa": "کیسا",
    "ho": "ہو",
    "aaj": "آج",
    "main": "میں",
    "mei": "میں",
    "mein": "میں",
    "tum": "تم",
    "tu": "تو",
    "to": "تو",
    "bahut": "بہت",
    "bohat": "بہت",
    "bht": "بہت",
    "achha": "اچھا",
    "acha": "اچھا",
    "theek": "ٹھیک",
    "shukriya": "شکریہ",
    "thanks": "شکریہ",
    "allah": "اللہ",
    "hafiz": "حافظ",
}


def detect_script(token: str) -> str:
    if re.search(r"[\u0600-\u06FF]", token):
        return "urdu_script"
    if re.search(r"[a-zA-Z]", token):
        return "roman_urdu"
    return "other"


def normalize_text(text: str) -> str:
    """Rule-based code-switch-aware normalization stub.

    Replaces known Roman-Urdu tokens with Urdu script and leaves other tokens
    untouched. This is sufficient for the Day-1 skeleton; it should be replaced
    by a frequency-derived or learned transliterator using Roman-Urdu-Parl.
    """
    tokens = text.split()
    normalized_tokens: List[str] = []
    for token in tokens:
        lower = token.lower().strip(".,!?؛،")
        if lower in ROMAN_TO_URDU:
            normalized_tokens.append(ROMAN_TO_URDU[lower])
        else:
            normalized_tokens.append(token)
    return " ".join(normalized_tokens)


def normalize_with_segments(text: str) -> Tuple[str, float, List[Dict]]:
    tokens = text.split()
    segments: List[Dict] = []
    normalized_tokens: List[str] = []
    confident = 0
    for token in tokens:
        script = detect_script(token)
        lower = token.lower().strip(".,!?؛،")
        mapping = ROMAN_TO_URDU.get(lower)
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
