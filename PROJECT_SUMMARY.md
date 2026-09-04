# UrduStack — Project Summary

## Context

UrduStack is a code-switch-aware Urdu NLP infrastructure layer built as a hackathon MVP in 2 days. It provides a unified pipeline for Urdu text normalization, risk scoring, speech-to-text, named entity recognition, and lexical simplification — designed to handle the reality of Pakistani digital text where Roman Urdu, Urdu script, and English mix freely in the same sentence.

**Author:** Munaza Tariq
**Stack:** Python 3.11, FastAPI, Gradio, PyTorch, Hugging Face Transformers, PEFT (LoRA), FAISS, Whisper
**Deployment:** Google Colab (T4 GPU training), Gradio share link (live demo)
**Repo:** github.com/munazat/UrduStack

---

## Architecture

```
Input (Urdu / Roman Urdu / English mix)
  │
  ├── Normalization Pipeline (3-tier cascade)
  │     1. Frequency map (6.37M parallel sentences → JSON lookup)
  │     2. Static dictionary (467 Roman→Urdu word mappings)
  │     3. RAG suggestion (FAISS char-3-gram TF-IDF similarity)
  │     4. Phonetic transliteration (greedy longest-match fallback)
  │
  ├── Risk Scorer (LoRA XLM-RoBERTa-base)
  │     → Score + calibrated confidence + risk level
  │     → Ablation-based per-word contribution (top 5 driving phrases)
  │
  ├── NER (XLM-RoBERTa WikiAnn)
  │     → PERSON, LOCATION, ORGANIZATION, DATE, MISC entities
  │
  ├── Speech-to-Text (OpenAI Whisper base, language="ur")
  │     → Urdu transcription with speech confidence
  │
  └── Lexical Simplification
        → Complex Urdu → simpler Urdu (19-entry dictionary)
        → Vocabulary complexity scoring
```

---

## Features

### 1. Code-Switch-Aware Normalization
Detects whether each token is Urdu script, Roman Urdu, or other. Runs a 3-tier cascade: frequency-map lookup (built from 6.37M parallel sentences), static 467-word dictionary, FAISS retrieval-augmented suggestion, then phonetic transliteration as last resort. English words, URLs, and numbers pass through untouched.

### 2. Explainable Risk Scoring
LoRA-fine-tuned XLM-RoBERTa-base for binary toxic/scam classification. Outputs a risk score (0–1), calibrated confidence via temperature scaling (T=1.409), risk level (low/medium/high), and the top 5 words driving the score using ablation-based contribution analysis. Falls back to a 16-pattern heuristic scorer when the model is unavailable.

### 3. Named Entity Recognition
XLM-RoBERTa trained on WikiAnn (covers Urdu). Input is normalized to Urdu script first so Roman Urdu entities are detected too. Labels mapped from PER/LOC/ORG to PERSON/LOCATION/ORGANIZATION. Character offsets remapped back to original text.

### 4. Speech-to-Text
OpenAI Whisper base model configured for Urdu. Accepts recorded or uploaded audio. Outputs transcription with speech confidence (1 - no_speech_prob). Transcribed text feeds into the same normalization + risk pipeline.

### 5. Lexical Simplification
Replaces 19 formal/complex Urdu words with simpler everyday alternatives. Handles multi-word phrases. Auto-normalizes Roman Urdu input so it works on both scripts. Reports vocabulary complexity ratio.

### 6. Active Learning Loop
Feedback endpoint collects user corrections. Feedback consumer script filters low-confidence and incorrect rows, deduplicates, and produces a retraining-ready CSV that can be merged back into the training set.

---

## Datasets

| Dataset | Source | Rows | Role |
|---|---|---|---|
| Roman-Urdu-Parl | `Mavkif/Roman-Urdu-Parl-split` (HF) | 6.37M | Frequency map for normalization (Roman→Urdu parallel corpus) |
| Roman-Urdu-Toxic-Corpus (PURUTT) | `hafiz-hassaan-saeed/Roman-Urdu-Toxic-Corpus` (HF) | 72,700 | Primary training data — toxic (label=1) vs clean (label=0) |
| Roman Urdu Hate Speech | `community-datasets/roman_urdu_hate_speech` (HF) | ~variable | Supplementary toxic samples (Coarse_Grained, label inverted) |
| Urdu Spam Dataset | `hamza-amin/urdu-spam-dataset` (HF) | ~variable | Supplementary spam samples |
| Synthetic Scam Data | Generated via `scripts/generate_scam_data.py` | 1,500 | Template-based scam text across 7 categories (job, lottery, phishing, investment, charity, shopping, loan) |
| UrduSpeech / Common Voice | `humairawan/UrduSpeech` / `mozilla-foundation/common_voice_17_0` (HF) | 50 eval samples | Whisper WER/CER evaluation |

**Combined training set:** ~80k rows after deduplication, class-weighted loss compensates for imbalance.

---

## Training Pipeline

**Base model:** `xlm-roberta-base` (270M parameters)
**Fine-tuning method:** LoRA (r=16, alpha=32, dropout=0.1, target: query/key/value/dense layers)
**Training config:**
- Learning rate: 2e-4, batch size: 16, 5 epochs
- Max samples: 70,000 train / 5,000 val / 5,000 test
- Class-weighted CrossEntropyLoss (custom Trainer subclass)
- Early stopping: patience 2 on validation loss
- FP16 mixed precision on T4 GPU
- Custom `_TokenizedDataset` (avoids HF datasets/torchvision Colab crash)

**Calibration:** Grid search over 100 temperature values [0.5, 5.0] on validation set → T = 1.409
**Runtime:** ~60–90 minutes on Colab free-tier T4 GPU

---

## Evaluation Metrics

### Risk Scorer
- **Test set:** accuracy, F1, precision, recall (computed at end of training)
- **Adversarial test suite:** 12 red-team cases covering leetspeak, spacing evasion, misspelling, mixed-script attacks, Roman Urdu scam
- **Calibration:** Temperature scaling verified on held-out validation set

### Whisper Speech-to-Text
- **WER** (Word Error Rate) on 50 Urdu speech samples
- **CER** (Character Error Rate) on same samples
- Evaluated on UrduSpeech with Common Voice as fallback

### NER
- Entity-level precision via model confidence scores
- Tested on Urdu-script and Roman Urdu input

---

## Problems Faced & Solutions

| Problem | Root Cause | Solution |
|---|---|---|
| Training crash: `KeyError: 'eval_f1'` at 20% | Dataset (83k rows) smaller than requested 110k | Auto-shrink logic: adjusts train size when dataset < requested total; reduced max_samples to 70k |
| Colab idle disconnect after ~90 min | Free-tier timeout, VM recycled → all files wiped | Auto-download: zip + `files.download()` triggers browser download immediately after training completes |
| Colab GPU limits exhausted | Free-tier has per-account GPU quotas | Rotated to fresh Google accounts for training |
| `FileNotFoundError: combined_risk.csv` | Git clone created nested `UrduStack/UrduStack` directory | Detect and remove nested clone, `os.chdir` into correct directory |
| NER producing garbage output | Model `Davlan/xlm-roberta-base-ner` trained on African languages, not Urdu | Switched to `wietsedv/xlm-roberta-base-ner` (WikiAnn, covers Urdu); normalize Roman Urdu before extraction; map PER/LOC/ORG → PERSON/LOCATION/ORGANIZATION |
| Simplify producing garbage output | Broken dictionary: English mappings (`"استعمال": "use"`), identity mappings, Hindi words, multi-word keys never matched | Rewrote dictionary (19 clean entries), multi-word phrase matching before single words, Roman Urdu support via normalization |
| HF datasets/torchvision crash on Colab | `VideoReader` import error at batch collation time | Custom `_TokenizedDataset` (plain `torch.utils.data.Dataset`) bypasses HF formatter entirely |
| pip install failures on Colab | Transient network issues, torchao conflicts | Retry logic (2 attempts with 5s delay), uninstall torchao before install |
| PEFT fails to restore classifier weights | `modules_to_save` sometimes not restored on load | Direct safetensors read + manual state_dict patch for classifier keys |
| pandas 3.0.5 deprecation warnings | Colab pip resolves newer pandas | Unpinned pandas version, accept harmless warnings |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Model load status |
| POST | `/normalize` | Code-switch-aware Roman Urdu → Urdu normalization |
| POST | `/risk-score` | Risk classification with explanation |
| POST | `/transcribe` | Urdu speech-to-text |
| POST | `/ner` | Named entity extraction |
| POST | `/simplify` | Lexical simplification |
| POST | `/analyze` | Full pipeline (normalize + risk + NER) |
| POST | `/feedback` | Active learning feedback submission |

---

## Gradio Demo (4 Tabs)

1. **Text Analysis** — Enter Urdu/Roman Urdu/English mix → get normalized text, risk score, confidence, explanation, flagged phrases
2. **Speech-to-Text** — Record or upload Urdu audio → transcription + normalization + risk analysis
3. **Named Entities** — Extract people, places, organizations from text
4. **Simplify** — Replace complex Urdu words with simpler alternatives + complexity score

---

## Project Structure (25 Python files, ~2,800 lines)

```
UrduStack/
├── app.py                        # HF Spaces entrypoint
├── playground.py                 # 4-tab Gradio demo
├── demo_job_scam.py              # Standalone job-scam checker
├── requirements.txt              # 20 dependencies
├── Dockerfile                    # python:3.11-slim container
├── README.md                     # Docs + HF Spaces metadata
├── app/
│   ├── main.py                   # FastAPI app
│   ├── api/endpoints.py          # 8 API routes
│   ├── models/
│   │   ├── risk_model.py         # LoRA XLM-RoBERTa risk scorer
│   │   ├── ner_model.py         # WikiAnn NER
│   │   └── model_manager.py     # Lazy model lifecycle
│   └── utils/
│       ├── normalization.py      # 3-tier normalizer
│       ├── rag_normalize.py      # FAISS retrieval-augmented lookup
│       ├── roman_urdu_map.py     # 467-word static dictionary
│       ├── transliterate.py      # Phonetic Roman→Urdu fallback
│       ├── transcription.py      # Whisper speech-to-text
│       ├── simplify.py           # Lexical simplification
│       └── risk.py               # Heuristic fallback scorer
├── scripts/
│   ├── train_risk_model.py       # LoRA fine-tuning + calibration
│   ├── build_normalizer_map.py   # Frequency map from parallel corpus
│   ├── generate_scam_data.py     # Synthetic scam data generator
│   └── consume_feedback.py       # Active learning feedback consumer
├── notebooks/
│   └── train_risk_model_colab.ipynb  # Hardened Colab training notebook
├── models/
│   ├── temperature.txt           # Calibrated temperature (1.409)
│   └── risk_lora/                # Trained LoRA adapter + tokenizer
├── tests/
│   └── adversarial_cases.py      # 12-case red-team test suite
└── static/
    └── index.html                # Vanilla JS frontend
```

---

## Key Technical Decisions

1. **LoRA over full fine-tuning** — 4.5MB adapter vs 1.1GB full model; fast iteration, easy to ship
2. **XLM-RoBERTa over Urdu-specific models** — Handles Roman Urdu natively without script conversion at the model level
3. **3-tier normalization cascade** — Dictionary first (exact), RAG second (fuzzy), transliteration last (phonetic) — maximizes accuracy while ensuring every word gets an Urdu-script output
4. **Temperature calibration** — Grid search on validation set prevents overconfident predictions
5. **Ablation-based contributions** — Remove each word, measure score drop → shows users *why* the model flagged the text
6. **Class-weighted loss** — Handles toxic/clean imbalance without resampling
7. **Heuristic fallback** — 16-pattern keyword scorer activates when model can't load (e.g., no torch installed), so the API always returns something useful

---

## Limitations & Future Work

- **Adversarial tests not re-run** against the trained model (stale heuristic results from early development)
- **NER offset mapping** assumes 1:1 token alignment; multi-word normalizer expansions can desync character positions
- **No batch inference** — each text is processed individually (fine for demo, slow at scale)
- **Frequency map not committed** — `data/processed/roman_urdu_freq.json` is built on Colab but not in the repo; normalization falls back to the 467-word static dictionary locally
- **Whisper base model** — `small` or `medium` would improve Urdu WER significantly but need more VRAM
- **No model versioning** — retraining overwrites the adapter; no experiment tracking or model registry
- **README out of date** — documents only 4 of 8 API endpoints
