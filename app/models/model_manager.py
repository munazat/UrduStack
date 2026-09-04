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
        """Run the full unified analysis pipeline on a single input.

        Pipeline cascade:
        1. Normalize (code-switch detection → Urdu script)
        2. Risk scoring (LoRA model or heuristic fallback)
        3. NER (on normalized text for entity extraction)
        4. Entity context enrichment (entities inform risk explanation)
        5. Simplify (risk explanation → plain Urdu for end users)
        6. Recommendation (actionable advice from risk level + entities)
        """
        from app.utils.normalization import normalize_with_segments
        from app.utils.simplify import simplify

        normalized, norm_conf, segments = normalize_with_segments(text)
        score, rconf, risk_level, flagged, explanation = self.risk_model.score(text)
        entities = self.ner_model.extract_entities(normalized)

        entity_types = {e["entity_group"] for e in entities}
        has_org = "ORGANIZATION" in entity_types
        has_person = "PERSON" in entity_types
        has_location = "LOCATION" in entity_types

        entity_context = []
        if entities:
            orgs = [e["word"] for e in entities if e["entity_group"] == "ORGANIZATION"]
            persons = [e["word"] for e in entities if e["entity_group"] == "PERSON"]
            locations = [e["word"] for e in entities if e["entity_group"] == "LOCATION"]
            if orgs:
                entity_context.append(
                    f"Mentioned organizations: {', '.join(orgs)}"
                )
            if persons:
                entity_context.append(
                    f"Mentioned persons: {', '.join(persons)}"
                )
            if locations:
                entity_context.append(
                    f"Mentioned locations: {', '.join(locations)}"
                )
        if score >= 0.4 and not has_org:
            entity_context.append(
                "No verifiable organization mentioned in flagged content."
            )
        if score >= 0.4 and not has_person and not has_org:
            entity_context.append(
                "No identifiable entity source — treat with caution."
            )

        simplified_explanation, _changes = simplify(explanation)

        recommendation = self._generate_recommendation(
            risk_level, flagged, entities, entity_context
        )

        return {
            "normalized": normalized,
            "norm_confidence": norm_conf,
            "segments": segments,
            "risk_score": score,
            "risk_confidence": rconf,
            "risk_level": risk_level,
            "flagged_phrases": flagged,
            "explanation": explanation,
            "simplified_explanation": simplified_explanation,
            "entities": entities,
            "entity_context": entity_context,
            "recommendation": recommendation,
        }

    @staticmethod
    def _generate_recommendation(
        risk_level: str,
        flagged: list,
        entities: list,
        entity_context: list,
    ) -> str:
        if risk_level == "high":
            parts = [
                "Strong indicators of scam or toxic content detected.",
                "Do not share money, personal details, or click any links.",
            ]
            if not any(
                "organization" in ctx.lower() for ctx in entity_context
            ):
                parts.append(
                    "No verifiable organization is behind this message."
                )
            return " ".join(parts)
        if risk_level == "medium":
            parts = ["Some suspicious patterns detected."]
            if flagged:
                top = flagged[0]["phrase"] if flagged else ""
                parts.append(f"Verify the claim about '{top}' independently.")
            parts.append(
                "Contact the organization through their official website "
                "or phone number before responding."
            )
            return " ".join(parts)
        return "No significant risk indicators detected. Standard caution applies."


_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    global _manager
    if _manager is None:
        _manager = ModelManager()
    return _manager
