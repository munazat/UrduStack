from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel, Field
from typing import List, Dict

from app.models.risk_model import RiskModel
from app.utils.normalization import normalize_with_segments
from app.utils.transcription import transcribe_audio

router = APIRouter()

# Load risk model once at startup. Falls back to heuristic if no adapter exists.
risk_model = RiskModel()


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


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        models_loaded={
            "normalizer": True,  # rule-based normalizer is always available
            "risk_scorer": risk_model.is_loaded,
        },
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
    score, confidence, risk_level, flagged_phrases, explanation = risk_model.score(
        payload.text
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
