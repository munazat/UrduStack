import os
from pathlib import Path
from typing import Dict, List, Tuple

from app.utils.risk import compute_risk_score as heuristic_score

# Optional heavy imports are deferred so the API can start without torch/transformers
# installed if only the heuristic path is used.

MODEL_PATH = Path(os.getenv("RISK_MODEL_PATH", "models/risk_lora"))
TEMPERATURE_PATH = Path(os.getenv("RISK_TEMPERATURE_PATH", "models/temperature.txt"))


class RiskModel:
    """Wrapper that loads a LoRA fine-tuned XLM-RoBERTa adapter if available,
    otherwise falls back to the heuristic keyword scorer."""

    def __init__(self, model_path: Path | str = MODEL_PATH):
        self.model_path = Path(model_path)
        self.tokenizer = None
        self.model = None
        self.temperature = 1.0
        self.device = "cpu"
        self._load()

    def _load(self):
        if not self.model_path.exists():
            return
        try:
            import torch
            from peft import PeftModel
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            if torch.cuda.is_available():
                self.device = "cuda"

            base_name = "xlm-roberta-base"
            base = AutoModelForSequenceClassification.from_pretrained(base_name)
            self.model = PeftModel.from_pretrained(base, self.model_path)
            self.model = self.model.to(self.device).eval()
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)

            if TEMPERATURE_PATH.exists():
                self.temperature = float(TEMPERATURE_PATH.read_text().strip())
        except Exception as exc:
            print(f"Could not load risk model from {self.model_path}: {exc}")
            self.model = None
            self.tokenizer = None

    @property
    def is_loaded(self) -> bool:
        return self.model is not None and self.tokenizer is not None

    def _tokenize(self, text: str, max_length: int = 128):
        return self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_length,
        )

    def score(self, text: str) -> Tuple[float, float, str, List[Dict[str, float]], str]:
        if not self.is_loaded:
            return heuristic_score(text)

        import torch

        inputs = self._tokenize(text)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.no_grad():
            logits = self.model(**inputs).logits
            scaled = logits / self.temperature
            probs = torch.softmax(scaled, dim=-1)
            risk_prob = probs[0, 1].item()
            confidence = max(risk_prob, 1 - risk_prob)

        score = round(risk_prob, 2)
        confidence = round(confidence, 2)
        risk_level = "high" if score >= 0.7 else "medium" if score >= 0.4 else "low"
        flagged = self._contribution_scores(text)
        explanation = (
            f"{risk_level.capitalize()} risk: model confidence {confidence:.2f}."
        )
        return score, confidence, risk_level, flagged, explanation

    def _contribution_scores(self, text: str) -> List[Dict[str, float]]:
        """Ablation-based contribution of each word to the risk score."""
        words = text.split()
        if len(words) <= 1:
            return []

        base_score = self._raw_risk(text)
        contributions: List[Dict[str, float]] = []
        for i, word in enumerate(words):
            ablated = " ".join(w for j, w in enumerate(words) if j != i)
            ablated_score = self._raw_risk(ablated)
            delta = max(0.0, base_score - ablated_score)
            if delta > 0.01:
                contributions.append({"phrase": word, "contribution": round(delta, 3)})
        contributions.sort(key=lambda x: x["contribution"], reverse=True)
        return contributions[:5]

    def _raw_risk(self, text: str) -> float:
        if not self.is_loaded:
            return 0.0
        import torch

        inputs = self._tokenize(text)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.no_grad():
            logits = self.model(**inputs).logits
            scaled = logits / self.temperature
            probs = torch.softmax(scaled, dim=-1)
            return probs[0, 1].item()
