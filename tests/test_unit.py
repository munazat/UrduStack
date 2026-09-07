"""Unit tests for UrduStack utility modules.

Run with: pytest tests/test_unit.py -v

These tests cover the heuristic scorer, lexical simplifier, and
text-collapse preprocessor. The full normalization pipeline and
model-backed scorer need torch/transformers and are tested via
run_evaluation.py on Colab.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_HAS_NUMPY = True
try:
    import numpy  # noqa: F401
except ImportError:
    _HAS_NUMPY = False

skip_no_numpy = pytest.mark.skipif(
    not _HAS_NUMPY, reason="numpy required for normalization module"
)


class TestHeuristicRiskScorer:

    def test_clean_text_low_score(self):
        from app.utils.risk import compute_risk_score

        score, conf, level, flagged, expl = compute_risk_score(
            "aaj mausam bohat acha hai"
        )
        assert score == 0.0
        assert level == "low"
        assert flagged == []

    def test_toxic_text_high_score(self):
        from app.utils.risk import compute_risk_score

        score, conf, level, flagged, expl = compute_risk_score("kutta kamina")
        assert score >= 0.25
        assert len(flagged) >= 1
        assert any(p["phrase"] == "kutta" for p in flagged)

    def test_scam_text_multiple_patterns(self):
        from app.utils.risk import compute_risk_score

        score, conf, level, flagged, expl = compute_risk_score(
            "job available 50000 per week send processing fee"
        )
        assert score >= 0.7
        assert level == "high"
        phrases = [p["phrase"] for p in flagged]
        assert "processing fee" in phrases
        assert "50000 per week" in phrases
        assert "job available" in phrases

    def test_case_insensitive(self):
        from app.utils.risk import compute_risk_score

        score_lower, _, _, _, _ = compute_risk_score("send money now")
        score_upper, _, _, _, _ = compute_risk_score("SEND MONEY NOW")
        assert score_lower == score_upper

    def test_score_capped_at_099(self):
        from app.utils.risk import compute_risk_score

        text = "processing fee registration fee advance payment send money 50000 per week"
        score, _, _, _, _ = compute_risk_score(text)
        assert score <= 0.99

    def test_confidence_formula(self):
        from app.utils.risk import compute_risk_score

        score, confidence, _, _, _ = compute_risk_score("kutta")
        expected_conf = round(0.5 + 0.5 * score, 2)
        assert confidence == expected_conf

    def test_risk_level_thresholds(self):
        from app.utils.risk import compute_risk_score

        _, _, level_low, _, _ = compute_risk_score("hello world")
        assert level_low == "low"

        _, _, level_high, _, _ = compute_risk_score(
            "madarchod benchod bhosri chutiya"
        )
        assert level_high == "high"

    def test_empty_text(self):
        from app.utils.risk import compute_risk_score

        score, conf, level, flagged, expl = compute_risk_score("")
        assert score == 0.0
        assert level == "low"
        assert flagged == []


class TestSimplify:

    def test_empty_text(self):
        from app.utils.simplify import simplify

        text, changes = simplify("")
        assert text == ""
        assert changes == []

    def test_no_complex_words(self):
        from app.utils.simplify import simplify

        text, changes = simplify("یہ ایک سادہ جملہ ہے")
        assert changes == []

    def test_complex_word_replaced(self):
        from app.utils.simplify import simplify

        text, changes = simplify("یہ بہت ضروری کام ہے")
        assert len(changes) >= 1
        originals = [c["original"] for c in changes]
        assert "ضروری" in originals

    def test_punctuation_preserved(self):
        from app.utils.simplify import simplify

        text, changes = simplify("کیا یہ ضروری ہے؟")
        assert "؟" in text

    def test_vocabulary_level_clean(self):
        from app.utils.simplify import get_vocabulary_level

        result = get_vocabulary_level("یہ ایک سادہ جملہ ہے")
        assert result["complex_words"] == 0
        assert result["complexity_ratio"] == 0.0

    def test_vocabulary_level_complex(self):
        from app.utils.simplify import get_vocabulary_level

        result = get_vocabulary_level("حکومت نے ضروری تعلیم کا اعلان کیا")
        assert result["complex_words"] >= 2
        assert result["complexity_ratio"] > 0

    def test_vocabulary_level_empty(self):
        from app.utils.simplify import get_vocabulary_level

        result = get_vocabulary_level("")
        assert result["total_words"] == 0

    def test_dictionary_has_19_entries(self):
        from app.utils.simplify import COMPLEX_TO_SIMPLE

        assert len(COMPLEX_TO_SIMPLE) == 19


@skip_no_numpy
class TestCollapseSpacedText:

    def test_normal_text_unchanged(self):
        from app.utils.normalization import collapse_spaced_text

        assert collapse_spaced_text("hello world") == "hello world"

    def test_spaced_chars_collapsed(self):
        from app.utils.normalization import collapse_spaced_text

        result = collapse_spaced_text("k u t t a")
        assert result == "kutta"

    def test_mixed_spaced_and_normal(self):
        from app.utils.normalization import collapse_spaced_text

        result = collapse_spaced_text("yar k u t t a mat bolo")
        assert "kutta" in result
        assert "yar" in result
        assert "mat" in result

    def test_spaced_scam_text(self):
        from app.utils.normalization import collapse_spaced_text

        result = collapse_spaced_text(
            "s e n d p r o c e s s i n g f e e"
        )
        assert "send" in result
        assert "processing" in result
        assert "fee" in result


@skip_no_numpy
class TestDetectScript:

    def test_urdu_script(self):
        from app.utils.normalization import detect_script

        assert detect_script("ضروری") == "urdu_script"

    def test_roman_urdu(self):
        from app.utils.normalization import detect_script

        assert detect_script("kutta") == "roman_urdu"

    def test_numbers(self):
        from app.utils.normalization import detect_script

        assert detect_script("12345") == "other"


class TestRiskLevelFunction:

    def test_high_threshold(self):
        from app.utils.risk import _risk_level

        assert _risk_level(0.7) == "high"
        assert _risk_level(0.85) == "high"
        assert _risk_level(0.99) == "high"

    def test_medium_threshold(self):
        from app.utils.risk import _risk_level

        assert _risk_level(0.4) == "medium"
        assert _risk_level(0.55) == "medium"
        assert _risk_level(0.69) == "medium"

    def test_low(self):
        from app.utils.risk import _risk_level

        assert _risk_level(0.0) == "low"
        assert _risk_level(0.39) == "low"


class TestHeuristicPatterns:

    def test_23_patterns_defined(self):
        from app.utils.risk import _PHRASE_DEFS, _WORD_PATTERNS

        total = len(_PHRASE_DEFS) + len(_WORD_PATTERNS)
        assert total == 23

    def test_all_contributions_positive(self):
        from app.utils.risk import _PHRASE_DEFS, _WORD_PATTERNS

        for name, weight, _ in _PHRASE_DEFS:
            assert weight > 0, f"Pattern '{name}' has non-positive weight"
        for word, weight in _WORD_PATTERNS.items():
            assert weight > 0, f"Pattern '{word}' has non-positive weight"

    def test_toxic_patterns_present(self):
        from app.utils.risk import _WORD_PATTERNS

        toxic_words = ["kutta", "madarchod", "benchod", "bhosri", "chutiya"]
        for word in toxic_words:
            assert word in _WORD_PATTERNS

    def test_scam_patterns_present(self):
        from app.utils.risk import _PHRASE_DEFS

        phrase_names = [name for name, _, _ in _PHRASE_DEFS]
        scam_phrases = ["processing fee", "send money", "click here"]
        for phrase in scam_phrases:
            assert phrase in phrase_names


class TestTypoCorrection:

    def test_typo_map_has_entries(self):
        from app.utils.risk import _TYPO_MAP

        assert len(_TYPO_MAP) > 30

    def test_corrects_procesing(self):
        from app.utils.risk import _correct_typos

        assert _correct_typos("send procesing fee") == "send processing fee"

    def test_corrects_availble(self):
        from app.utils.risk import _correct_typos

        assert _correct_typos("job availble") == "job available"

    def test_preserves_clean_text(self):
        from app.utils.risk import _correct_typos

        assert _correct_typos("software engineer required") == "software engineer required"

    def test_misspelled_scam_detected(self):
        from app.utils.risk import compute_risk_score

        score, _, level, flagged, _ = compute_risk_score(
            "job availble, 50000 per wek, send procesing fee"
        )
        assert score >= 0.4
        phrases = [p["phrase"] for p in flagged]
        assert "processing fee" in phrases

    def test_no_self_referencing_entries(self):
        from app.utils.risk import _TYPO_MAP

        for typo, correct in _TYPO_MAP.items():
            assert typo != correct, f"'{typo}' maps to itself"


class TestRiskCategorization:

    def test_job_scam_detected(self):
        from app.utils.risk import categorize_risk

        flagged = [
            {"phrase": "processing fee", "contribution": 0.56},
            {"phrase": "50000 per week", "contribution": 0.28},
        ]
        result = categorize_risk(flagged)
        assert "job_scam" in result["categories"]
        assert result["primary_category"] == "job_scam"
        assert "fake job" in result["advice"].lower()

    def test_harassment_detected(self):
        from app.utils.risk import categorize_risk

        flagged = [
            {"phrase": "kutta", "contribution": 0.41},
            {"phrase": "kamina", "contribution": 0.41},
        ]
        result = categorize_risk(flagged)
        assert "harassment" in result["categories"]
        assert result["primary_category"] == "harassment"
        assert "block" in result["advice"].lower()

    def test_mixed_categories_ranked(self):
        from app.utils.risk import categorize_risk

        flagged = [
            {"phrase": "processing fee", "contribution": 0.56},
            {"phrase": "kutta", "contribution": 0.41},
        ]
        result = categorize_risk(flagged)
        assert len(result["categories"]) == 2
        assert result["primary_category"] == "job_scam"
        assert "harassment" in result["categories"]

    def test_empty_flagged_returns_empty(self):
        from app.utils.risk import categorize_risk

        result = categorize_risk([])
        assert result["categories"] == []
        assert result["primary_category"] is None
        assert result["advice"] == ""

    def test_all_patterns_have_category(self):
        from app.utils.risk import _PHRASE_DEFS, _WORD_PATTERNS, _PHRASE_CATEGORY

        for name, _, _ in _PHRASE_DEFS:
            assert name in _PHRASE_CATEGORY, f"Phrase '{name}' missing from _PHRASE_CATEGORY"
        for word in _WORD_PATTERNS:
            assert word in _PHRASE_CATEGORY, f"Word '{word}' missing from _PHRASE_CATEGORY"

    def test_category_advice_is_specific(self):
        from app.utils.risk import _CATEGORY_ADVICE

        for cat, advice in _CATEGORY_ADVICE.items():
            assert len(advice) > 50, f"Category '{cat}' advice too generic"
            assert cat != "job_scam" or "fee" in advice.lower()
            assert cat != "harassment" or "block" in advice.lower()
