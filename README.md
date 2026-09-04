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

## Current status (Tier 1 + Tier 2 MVP)

- [x] FastAPI skeleton with all four endpoints
- [x] Rule-based normalizer with starter + dataset-ready frequency-map loader
- [x] Gradio playground
- [x] LoRA fine-tuning script for XLM-RoBERTa on PURUTT (Colab-ready)
- [x] Risk-model loader with temperature scaling + ablation-based phrase contributions
- [x] Adversarial red-teaming harness
- [ ] Real PURUTT dataset downloaded
- [ ] Real Roman-Urdu-Parl dataset downloaded
- [ ] Trained risk LoRA adapter
- [ ] Calibrated confidence validated
- [ ] Docker build verified
- [ ] Hugging Face Spaces deployment

### Honest adversarial baseline

With the heuristic placeholder scorer, `tests/adversarial_cases.py` currently passes **4/12** cases. This is expected: keyword matching fails on leetspeak, spacing tricks, and Roman-Urdu scam phrasing. The harness is in place so we can re-run it after training the LoRA model and document real robustness honestly.

## Next steps

1. Download PURUTT and Roman-Urdu-Parl into `data/raw/`.
2. Run `python scripts/build_normalizer_map.py` to build the frequency map.
3. Run `scripts/train_risk_model.py` in Google Colab to train the LoRA adapter.
4. Place the trained adapter in `models/risk_lora/` and `models/temperature.txt`.
5. Re-run `tests/adversarial_cases.py` and update the README with the real score.
6. Deploy to Hugging Face Spaces.
