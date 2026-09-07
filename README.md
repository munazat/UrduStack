---
title: UrduStack Playground
emoji: "🇵🇰"
colorFrom: green
colorTo: teal
sdk: gradio
sdk_version: 5.1.0
app_file: playground.py
license: mit
---

# UrduStack

A unified, self-hosted, code-switch-aware Urdu NLP infrastructure layer for Urdu text and speech.

## What it does

- **Code-switch-aware normalization** — mixed Urdu script / Roman Urdu / English text → clean Urdu script.
- **Explainable risk scoring** — flags toxic / scam content with a calibrated confidence score and the phrases that drove the decision.
- **Speech-to-text (Tier 3)** — transcribes spoken Urdu and feeds it into the same pipeline.

## Architecture

![UrduStack Pipeline Architecture](static/architecture.png)

## API endpoints

| Method | Endpoint | Input | Output |
|---|---|---|---|
| GET | `/health` | — | `{status, models_loaded}` |
| POST | `/normalize` | `{text}` | `{normalized, confidence, segments}` |
| POST | `/risk-score` | `{text}` | `{score, confidence, risk_level, flagged_phrases, explanation}` |
| POST | `/transcribe` | audio file | `{text, confidence}` |
| POST | `/ner` | `{text}` | `{entities}` |
| POST | `/simplify` | `{text}` | `{simplified, changes, complexity}` |
| POST | `/analyze` | `{text}` | Full pipeline (normalize + risk + NER + simplify) |
| POST | `/feedback` | `{text, label, ...}` | `{stored}` |

## Project structure

```
app/
  api/         FastAPI routers
  models/      ML model definitions and checkpoints
  data/        Datasets and processed data
  utils/       Normalization, risk scoring, transcription helpers
scripts/       Training and data-preparation scripts
playground.py  Standalone Gradio UI
tests/         Adversarial red-teaming cases
```

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for interactive API documentation.

## Run the playground

```bash
pip install -r requirements.txt
python playground.py
```

Then open http://localhost:7860.

## Live demo (hackathon submission URL)

Open [`notebooks/launch_demo.ipynb`](notebooks/launch_demo.ipynb) in
Google Colab, enable the T4 GPU runtime, and run all 5 cells. After
3–5 minutes, cell 5 prints a public URL like:

    Running on public URL: https://<hash>.gradio.live

That URL is valid for **72 hours** and can be shared with anyone — no
login, no setup. If it expires, re-run the notebook to get a fresh one.

### What the evaluator sees

- **Text Analysis**: Urdu / Roman Urdu / code-switched text → normalized
  Urdu script, risk score with phrase-level contributions, NER entities,
  and a plain-language recommendation.
- **Speech Analysis**: record or upload Urdu audio → Whisper transcription
  → same analysis pipeline.
- **Comparison**: naive English keyword baseline vs. UrduStack — shows
  where normalization + fine-tuned model catches scams the baseline misses.

**Pipeline:** Normalize → Risk Score → NER → Entity Context → Simplify →
Recommendation. **Risk model:** LoRA XLM-RoBERTa, calibrated (T=1.41),
threshold 0.3, accuracy 88.8%, precision 97.0%, recall 75.6%, F1 85.0%.

## Build with Docker / Hugging Face Spaces

```bash
docker build -t urdustack .
docker run -p 7860:7860 urdustack
```

The container exposes port `7860` and runs `app.py`, which mounts the Gradio playground at `/` and keeps the FastAPI routes under `/health`, `/normalize`, `/risk-score`, `/transcribe`.

## Current status

### Core infrastructure
- [x] FastAPI endpoints: `/health`, `/normalize`, `/risk-score`, `/transcribe`
- [x] Code-switch-aware normalizer (dictionary + RAG + phonetic transliteration)
- [x] Frequency map builder (`scripts/build_normalizer_map.py` — runs on Colab, JSON not committed)
- [x] Synthetic scam data generator (job scams, lottery fraud, phishing, fee fraud)
- [x] Speech-to-text via Urdu Whisper
- [x] Named Entity Recognition (XLM-RoBERTa WikiANN)
- [x] Lexical simplification for plain-language explanations
- [x] Retrieval-augmented normalization (FAISS char-ngram index, seeded with 124 entries beyond static dict → 587 total phrases)

### Risk model
- [x] LoRA fine-tuned XLM-RoBERTa on PURUTT (72.7k samples, 5 epochs)
- [x] Temperature calibration (T=1.41)
- [x] Metrics: accuracy 88.8%, precision 97.0%, recall 75.6%, F1 85.0%
- [x] Max-ensemble scoring (LoRA + heuristic, takes higher score)
- [x] Four-pass heuristic detection: word-boundary regex, leetspeak normalization, typo correction (48 misspellings), fuzzy character-spacing regex
- [x] Ablation-based phrase contribution scoring
- [x] Class-weighted loss + early stopping

### Demo and evaluation
- [x] Unified Gradio dashboard (text, speech, comparison tabs)
- [x] Naive keyword baseline vs. full pipeline comparison mode
- [x] Active learning feedback loop (Gradio widget → CSV → retrain)
- [x] Visual explainability (phrase contribution bar chart)
- [x] PDF report export
- [x] Colab launch notebook with auto-detect model files
- [x] Adversarial red-teaming harness
- [x] 36 pytest unit tests (heuristic scorer, simplifier, preprocessor, typo correction)
- [x] Committed eval metrics JSON with real numbers
- [x] Spacing evasion mitigation (character-collapse preprocessing)
- [x] Architecture diagram

### Deployment
- [x] Docker-ready (`docker build -t urdustack .`)
- [x] Colab Gradio `share=True` for live public demo (72h URL)
- [x] HF Hub model card for LoRA adapter
- [x] All model files committed to repo (no manual upload needed)

### Known limitations
- **Recall gap:** 75.6% recall — model favors precision (97.0%) to
  avoid false positives.
- **Character-spaced evasion:** "k u t t a" style attacks mitigated by
  fuzzy character-spacing regex in the heuristic scorer and
  preprocessing collapse. Passes adversarial tests.
- **Domain shift:** Trained on social media text; formal/literary Urdu
  may perform differently.
- **Frequency map:** Tier-1 lookup built on Colab but not committed to
  repo; normalizer falls back to 467-word dictionary + RAG (seeded with
  124 additional domain-specific entries, 587 total phrases) + transliteration.

## Testing

### Unit tests
```bash
pip install pytest
pytest tests/test_unit.py -v
```
36 tests covering the heuristic scorer (8 tests), risk level thresholds
(3), pattern inventory (4), typo correction (6), lexical simplifier (8),
spacing-collapse preprocessor (4), and script detection (3). Normalization
tests skip gracefully when numpy is not installed.

### Full evaluation (requires GPU)
```bash
python tests/run_evaluation.py              # all 97 examples
python tests/run_evaluation.py --mode adversarial  # 12 red-team cases
python tests/run_adversarial_colab.py       # standalone adversarial runner
```

### Evaluation results

The trained LoRA adapter achieves on a 97-example test set:

| Metric | Score |
|---|---|
| Accuracy | 88.8% |
| Precision | 97.0% |
| Recall | 75.6% |
| F1 | 85.0% |

Full metrics: [`tests/eval_metrics_full_t0.4.json`](tests/eval_metrics_full_t0.4.json)

### Adversarial red-team results

The heuristic scorer with four-pass detection (word-boundary regex,
leetspeak normalization, typo correction, fuzzy character-spacing regex)
passes **12/12** adversarial cases, including leetspeak, character spacing,
misspellings, mixed-script, and Roman-Urdu scam phrasing. The max-ensemble
(LoRA + heuristic) is expected to match or exceed this on Colab GPU.
Re-run with `tests/run_adversarial_colab.py` to verify with the trained adapter.
