"""Phonetic Roman-Urdu → Urdu-script transliteration engine.

Uses greedy longest-match over bigram/trigram → single-char mappings,
so unknown Roman-Urdu words still render in Urdu script even when they
aren't in the word-level dictionary.
"""

_BIGRAMS = {
    "sh": "ش", "ch": "چ", "th": "تھ", "dh": "دھ",
    "gh": "غ", "ph": "پھ", "bh": "بھ", "jh": "جھ",
    "kh": "خ", "ai": "ی", "au": "و", "ee": "ی",
    "oo": "و", "ng": "نگ", "nh": "نھ",
}

_SINGLE = {
    "a": "ا", "b": "ب", "c": "ک", "d": "د", "e": "ے",
    "f": "ف", "g": "گ", "h": "ھ", "i": "ی", "j": "ج",
    "k": "ک", "l": "ل", "m": "م", "n": "ن", "o": "و",
    "p": "پ", "q": "ق", "r": "ر", "s": "س", "t": "ت",
    "u": "و", "v": "و", "w": "و", "x": "کس", "y": "ی",
    "z": "ز",
}


def transliterate(word: str) -> str:
    """Convert a Roman-Urdu word to an approximate Urdu script rendering."""
    text = word.lower()
    out: list[str] = []
    i = 0
    while i < len(text):
        if i + 1 < len(text):
            pair = text[i : i + 2]
            if pair in _BIGRAMS:
                out.append(_BIGRAMS[pair])
                i += 2
                continue
        ch = text[i]
        if ch in _SINGLE:
            out.append(_SINGLE[ch])
        else:
            out.append(ch)
        i += 1
    return "".join(out)
