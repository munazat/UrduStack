# UrduStack

A unified, self-hosted, code-switch-aware Urdu NLP infrastructure layer.

## What it does

- **Code-switch-aware normalization** — mixed Urdu script / Roman Urdu / English text → clean Urdu script.
- **Explainable risk scoring** — flags toxic / scam content with a calibrated confidence score and the phrases that drove the decision.
- **Speech-to-text (Tier 3)** — transcribes spoken Urdu and feeds it into the same pipeline.

## API endpoints

| Method | Endpoint | Input | Output |
|---|---|---|---|
| GET | `/health` | — | `{status, models_loaded}` |
| POST | `/normalize` | `{text}` | `{normalized, confidence, segments}` |
| POST | `/risk-score` | `{text}` | `{score, confidence, risk_level, flagged_phrases, explanation}` |
| POST | `/transcribe` | audio file | `{text, confidence}` |

## Project structure

```
app/
  api/         FastAPI routers
  models/      ML model definitions and checkpoints
  data/        Datasets and processed data
  utils/       Normalization, risk scoring, transcription helpers
```

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for interactive API documentation.

## Build with Docker

```bash
docker build -t urdustack .
docker run -p 8000:8000 urdustack
```

## Status

This is a runnable skeleton. The normalization and risk-score endpoints currently use heuristic placeholders so the API contract can be tested end-to-end. The next step is to replace them with the real datasets and fine-tuned models documented in the project plan.
