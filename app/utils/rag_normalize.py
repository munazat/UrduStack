"""Retrieval-augmented normalization using FAISS.

Builds a vector index of known Roman-Urdu phrases and their Urdu translations.
When an unknown word can't be found in the dictionary, retrieves the most
similar known word and uses its translation as a hint.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from app.utils.roman_urdu_map import ROMAN_TO_URDU

_SEED_PATH = Path("data/processed/rag_phrase_pairs.json")

_char_ngram_index = None
_index_phrases: List[str] = []
_index_translations: List[str] = []


def _char_ngrams(text: str, n: int = 3) -> List[str]:
    text = text.lower()
    return [text[i : i + n] for i in range(len(text) - n + 1)]


def _build_tfidf_vocab(
    phrases: List[str], n: int = 3
) -> Tuple[Dict[str, int], np.ndarray]:
    """Build character n-gram TF-IDF vectors for a list of phrases."""
    from collections import Counter

    ngram_docs = [_char_ngrams(p, n) for p in phrases]
    df = Counter()
    for doc in ngram_docs:
        df.update(set(doc))

    vocab: Dict[str, int] = {}
    for ngram in df:
        if ngram not in vocab:
            vocab[ngram] = len(vocab)

    n_phrases = len(phrases)
    n_vocab = len(vocab)
    tfidf = np.zeros((n_phrases, n_vocab), dtype=np.float32)

    for i, doc in enumerate(ngram_docs):
        counts = Counter(doc)
        total = max(len(doc), 1)
        for ngram, count in counts.items():
            idx = vocab[ngram]
            tf = count / total
            idf = np.log((n_phrases + 1) / (df[ngram] + 1)) + 1
            tfidf[i, idx] = tf * idf

    norms = np.linalg.norm(tfidf, axis=1, keepdims=True)
    norms[norms == 0] = 1
    tfidf /= norms

    return vocab, tfidf


def build_index():
    """Build the FAISS index from the Roman-Urdu dictionary."""
    global _char_ngram_index, _index_phrases, _index_translations

    phrases = list(ROMAN_TO_URDU.keys())
    translations = [ROMAN_TO_URDU[p] for p in phrases]

    if _SEED_PATH.exists():
        import json

        with _SEED_PATH.open("r", encoding="utf-8") as f:
            extra = json.load(f)
        for roman, urdu in extra.items():
            if roman not in ROMAN_TO_URDU:
                phrases.append(roman)
                translations.append(urdu)

    if not phrases:
        return

    _index_phrases = phrases
    _index_translations = translations

    try:
        import faiss

        vocab, tfidf = _build_tfidf_vocab(phrases)
        dim = tfidf.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(tfidf)
        _char_ngram_index = (vocab, index, tfidf)
    except ImportError:
        _char_ngram_index = None


def search_similar(query: str, top_k: int = 3, min_similarity: float = 0.5) -> List[Tuple[str, str, float]]:
    """Find the most similar known phrases to the query.

    Returns list of (roman_phrase, urdu_translation, similarity_score).
    """
    if _char_ngram_index is None:
        if _index_phrases:
            return []
        build_index()
        if _char_ngram_index is None:
            return []

    vocab, index, _ = _char_ngram_index

    query_ngrams = _char_ngrams(query)
    if not query_ngrams:
        return []

    from collections import Counter

    counts = Counter(query_ngrams)
    total = max(len(query_ngrams), 1)
    vec = np.zeros((1, _char_ngram_index[2].shape[1]), dtype=np.float32)
    for ngram, count in counts.items():
        if ngram in vocab:
            idx = vocab[ngram]
            tf = count / total
            idf = np.log((len(_index_phrases) + 1) / 2) + 1
            vec[0, idx] = tf * idf

    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm

    scores, indices = index.search(vec, min(top_k, len(_index_phrases)))

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or score < min_similarity:
            continue
        results.append(
            (_index_phrases[idx], _index_translations[idx], float(score))
        )
    return results


def suggest_translation(unknown_word: str) -> Optional[str]:
    """Suggest a translation for an unknown word using retrieval."""
    results = search_similar(unknown_word, top_k=1, min_similarity=0.6)
    if results:
        return results[0][1]
    return None
