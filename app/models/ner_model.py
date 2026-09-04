from __future__ import annotations

from typing import Dict, List


class NERModel:
    """Named Entity Recognition using XLM-RoBERTa trained on WikiAnn.

    Normalizes Roman Urdu to Urdu script before extraction so mixed-script
    input works. Falls back to empty results if the model cannot be loaded.
    """

    def __init__(self, model_name: str = "Davlan/xlm-roberta-base-wikiann-ner"):
        self.model_name = model_name
        self._pipe = None
        self._load_failed = False

    def _load(self):
        if self._pipe is not None or self._load_failed:
            return
        try:
            from transformers import pipeline

            self._pipe = pipeline(
                "ner",
                model=self.model_name,
                aggregation_strategy="simple",
                device=-1,
            )
        except Exception as exc:
            self._load_failed = True
            print(f"Could not load NER model: {exc}")
            print("Install with: pip install transformers torch")

    @property
    def is_loaded(self) -> bool:
        if self._pipe is None and not self._load_failed:
            self._load()
        return self._pipe is not None

    def extract_entities(self, text: str) -> List[Dict[str, str | float]]:
        """Extract named entities from Urdu / Roman Urdu text.

        Returns a list of dicts with keys:
            entity_group: PERSON, LOCATION, ORGANIZATION, DATE, MISC
            word: the entity text
            score: confidence (0-1)
            start: character offset in original text
            end: character offset in original text
        """
        if not text or not text.strip():
            return []
        if not self.is_loaded:
            return []

        from app.utils.normalization import normalize_text

        normalized = normalize_text(text)
        try:
            results = self._pipe(normalized)
        except Exception as exc:
            print(f"NER inference failed: {exc}")
            return []

        orig_offsets = self._build_offset_map(text, normalized)

        entities = []
        for r in results:
            entities.append(
                {
                    "entity_group": self._map_label(r["entity_group"]),
                    "word": r["word"].strip(),
                    "score": round(float(r["score"]), 3),
                    "start": orig_offsets.get(r["start"], 0),
                    "end": orig_offsets.get(
                        r["end"], len(text)
                    ),
                }
            )
        return entities

    @staticmethod
    def _build_offset_map(
        original: str, normalized: str
    ) -> Dict[int, int]:
        """Map character offsets from normalized text back to original."""
        orig_tokens = original.split()
        norm_tokens = normalized.split()

        mapping: Dict[int, int] = {0: 0}
        o = 0
        n = 0
        for ot, nt in zip(orig_tokens, norm_tokens):
            mapping[n] = o
            mapping[n + len(nt)] = o + len(ot)
            o += len(ot) + 1
            n += len(nt) + 1
        return mapping

    @staticmethod
    def _map_label(label: str) -> str:
        labels = {
            "PER": "PERSON",
            "LOC": "LOCATION",
            "ORG": "ORGANIZATION",
            "PERSON": "PERSON",
            "LOCATION": "LOCATION",
            "ORGANIZATION": "ORGANIZATION",
        }
        return labels.get(label, label)


_ner_model = None


def get_ner_model() -> NERModel:
    global _ner_model
    if _ner_model is None:
        _ner_model = NERModel()
    return _ner_model
