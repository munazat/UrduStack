"""Central model manager for UrduStack.

Orchestrates lazy loading, memory tracking, and lifecycle management for all
NLP models (risk scoring, NER, speech-to-text, normalization). Ensures only
necessary models are loaded into GPU memory.
"""

from typing import Dict, Optional


class ModelManager:
    """Singleton-style manager that loads models on demand and tracks GPU usage."""

    def __init__(self):
        self._risk_model = None
        self._ner_model = None
        self._transcription_model = None
        self._loaded: Dict[str, bool] = {}

    @property
    def risk_model(self):
        if self._risk_model is None:
            from app.models.risk_model import RiskModel
            self._risk_model = RiskModel()
            self._loaded["risk_scorer"] = self._risk_model.is_loaded
        return self._risk_model

    @property
    def ner_model(self):
        if self._ner_model is None:
            from app.models.ner_model import NERModel
            self._ner_model = NERModel()
            self._loaded["ner"] = self._ner_model.is_loaded
        return self._ner_model

    @property
    def transcription_model(self):
        if self._transcription_model is None:
            from app.utils.transcription import TranscriptionModel
            self._transcription_model = TranscriptionModel()
            self._loaded["transcription"] = self._transcription_model.is_loaded
        return self._transcription_model

    def status(self) -> Dict[str, bool]:
        return {
            "normalizer": True,
            "risk_scorer": self._loaded.get("risk_scorer", False),
            "ner": self._loaded.get("ner", False),
            "transcription": self._loaded.get("transcription", False),
            "rag_index": self._rag_index_loaded(),
        }

    def _rag_index_loaded(self) -> bool:
        try:
            from app.utils.rag_normalize import _char_ngram_index
            return _char_ngram_index is not None
        except ImportError:
            return False

    def preload_all(self):
        """Load all models upfront. Useful for benchmarks, not for production."""
        _ = self.risk_model
        _ = self.ner_model
        _ = self.transcription_model

    def unload(self, model_name: str):
        """Unload a model to free GPU memory."""
        if model_name == "risk_scorer" and self._risk_model is not None:
            self._risk_model = None
            self._loaded["risk_scorer"] = False
        elif model_name == "ner" and self._ner_model is not None:
            self._ner_model = None
            self._loaded["ner"] = False
        elif model_name == "transcription" and self._transcription_model is not None:
            self._transcription_model = None
            self._loaded["transcription"] = False

    def analyze_text(self, text: str) -> Dict:
        """Run all text analysis tasks on a single input."""
        from app.utils.normalization import normalize_with_segments

        normalized, norm_conf, segments = normalize_with_segments(text)
        score, rconf, risk_level, flagged, explanation = self.risk_model.score(text)
        entities = self.ner_model.extract_entities(text)

        return {
            "normalized": normalized,
            "norm_confidence": norm_conf,
            "segments": segments,
            "risk_score": score,
            "risk_confidence": rconf,
            "risk_level": risk_level,
            "flagged_phrases": flagged,
            "explanation": explanation,
            "entities": entities,
        }


_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    global _manager
    if _manager is None:
        _manager = ModelManager()
    return _manager
