from typing import Dict, List


class NERModel:
    """Named Entity Recognition using a multilingual XLM-RoBERTa NER model.

    Lazily loads the model on first use. Falls back to an empty result
    if the model cannot be loaded.
    """

    def __init__(self, model_name: str = "Davlan/xlm-roberta-base-ner"):
        self.model_name = model_name
        self._pipe = None

    def _load(self):
        if self._pipe is not None:
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
            print(f"Could not load NER model: {exc}")
            print("Install with: pip install transformers torch")

    @property
    def is_loaded(self) -> bool:
        if self._pipe is None:
            self._load()
        return self._pipe is not None

    def extract_entities(self, text: str) -> List[Dict[str, str | float]]:
        """Extract named entities from text.

        Returns a list of dicts with keys:
            entity_group: PERSON, LOCATION, ORGANIZATION, etc.
            word: the entity text
            score: confidence (0-1)
            start: character offset
            end: character offset
        """
        if not text or not text.strip():
            return []
        if not self.is_loaded:
            return []

        results = self._pipe(text)
        entities = []
        for r in results:
            entities.append(
                {
                    "entity_group": r["entity_group"],
                    "word": r["word"],
                    "score": round(float(r["score"]), 3),
                    "start": int(r["start"]),
                    "end": int(r["end"]),
                }
            )
        return entities


_ner_model = None


def get_ner_model() -> NERModel:
    global _ner_model
    if _ner_model is None:
        _ner_model = NERModel()
    return _ner_model
