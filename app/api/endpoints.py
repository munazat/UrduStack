import csv
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

from app.models.model_manager import get_model_manager
from app.utils.normalization import normalize_with_segments
from app.utils.transcription import transcribe_audio

router = APIRouter()

_FEEDBACK_PATH = Path("data/feedback.csv")
_FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)


class HealthResponse(BaseModel):
    status: str
    models_loaded: Dict[str, bool]


class NormalizeRequest(BaseModel):
    text: str = Field(..., min_length=1)


class Segment(BaseModel):
    original: str
    normalized: str
    detected_script: str


class NormalizeResponse(BaseModel):
    normalized: str
    confidence: float
    segments: List[Segment]


class RiskScoreRequest(BaseModel):
    text: str = Field(..., min_length=1)


class FlaggedPhrase(BaseModel):
    phrase: str
    contribution: float


class RiskScoreResponse(BaseModel):
    score: float
    confidence: float
    risk_level: str
    flagged_phrases: List[FlaggedPhrase]
    explanation: str


class TranscribeResponse(BaseModel):
    text: str
    confidence: float


class NERRequest(BaseModel):
    text: str = Field(..., min_length=1)


class NEREntity(BaseModel):
    entity_group: str
    word: str
    score: float
    start: int
    end: int


class NERResponse(BaseModel):
    entities: List[NEREntity]


class SimplifyRequest(BaseModel):
    text: str = Field(..., min_length=1)


class SimplificationChange(BaseModel):
    original: str
    simplified: str


class SimplifyResponse(BaseModel):
    simplified: str
    changes: List[SimplificationChange]
    complexity_ratio: float


class FeedbackRequest(BaseModel):
    text: str = Field(..., min_length=1)
    normalized: Optional[str] = None
    score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    correct_label: str = Field(..., pattern="^(correct|low_risk|medium_risk|high_risk|spam|not_spam)$")
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    status: str


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1)


class AnalyzeResponse(BaseModel):
    normalized: str
    norm_confidence: float
    risk_score: float
    risk_confidence: float
    risk_level: str
    flagged_phrases: List[FlaggedPhrase]
    explanation: str
    simplified_explanation: str
    entities: List[NEREntity]
    entity_context: List[str]
    recommendation: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    manager = get_model_manager()
    return HealthResponse(
        status="ok",
        models_loaded=manager.status(),
    )


@router.post("/normalize", response_model=NormalizeResponse)
def normalize(payload: NormalizeRequest) -> NormalizeResponse:
    normalized, confidence, segments = normalize_with_segments(payload.text)
    return NormalizeResponse(
        normalized=normalized,
        confidence=confidence,
        segments=segments,
    )


@router.post("/risk-score", response_model=RiskScoreResponse)
def risk_score(payload: RiskScoreRequest) -> RiskScoreResponse:
    manager = get_model_manager()
    score, confidence, risk_level, flagged_phrases, explanation = (
        manager.risk_model.score(payload.text)
    )
    return RiskScoreResponse(
        score=score,
        confidence=confidence,
        risk_level=risk_level,
        flagged_phrases=flagged_phrases,
        explanation=explanation,
    )


@router.post("/transcribe", response_model=TranscribeResponse)
def transcribe(audio: UploadFile = File(...)) -> TranscribeResponse:
    text = transcribe_audio(audio.file)
    return TranscribeResponse(text=text, confidence=0.0)


@router.post("/ner", response_model=NERResponse)
def ner(payload: NERRequest) -> NERResponse:
    manager = get_model_manager()
    entities = manager.ner_model.extract_entities(payload.text)
    return NERResponse(entities=[NEREntity(**e) for e in entities])


@router.post("/simplify", response_model=SimplifyResponse)
def simplify_text(payload: SimplifyRequest) -> SimplifyResponse:
    from app.utils.simplify import simplify, get_vocabulary_level

    simplified, changes = simplify(payload.text)
    level = get_vocabulary_level(payload.text)
    return SimplifyResponse(
        simplified=simplified,
        changes=[SimplificationChange(**c) for c in changes],
        complexity_ratio=level["complexity_ratio"],
    )


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_all(payload: AnalyzeRequest) -> AnalyzeResponse:
    manager = get_model_manager()
    result = manager.analyze_text(payload.text)
    return AnalyzeResponse(
        normalized=result["normalized"],
        norm_confidence=result["norm_confidence"],
        risk_score=result["risk_score"],
        risk_confidence=result["risk_confidence"],
        risk_level=result["risk_level"],
        flagged_phrases=[FlaggedPhrase(**p) for p in result["flagged_phrases"]],
        explanation=result["explanation"],
        simplified_explanation=result.get("simplified_explanation", ""),
        entities=[NEREntity(**e) for e in result["entities"]],
        entity_context=result.get("entity_context", []),
        recommendation=result.get("recommendation", ""),
    )


@router.post("/feedback", response_model=FeedbackResponse)
def feedback(payload: FeedbackRequest) -> FeedbackResponse:
    file_exists = _FEEDBACK_PATH.exists()
    with _FEEDBACK_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "timestamp",
                "text",
                "normalized",
                "score",
                "confidence",
                "correct_label",
                "comment",
            ],
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "text": payload.text,
                "normalized": payload.normalized or "",
                "score": payload.score,
                "confidence": payload.confidence,
                "correct_label": payload.correct_label,
                "comment": payload.comment or "",
            }
        )
    return FeedbackResponse(status="ok")
