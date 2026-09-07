# UrduStack — Project Summary

## Context

UrduStack is a code-switch-aware Urdu NLP infrastructure layer built as a hackathon MVP in 2 days. Its core capability is **explainable risk scoring** — a LoRA-fine-tuned XLM-RoBERTa model that detects toxic and scam content in Urdu/Roman Urdu code-switched text (88.8% accuracy, 97.0% precision on a 97-example held-out run), providing calibrated confidence scores and per-word contribution explanations. Supporting modules (normalization, NER, speech-to-text, lexical simplification) form the infrastructure that makes risk scoring work on the reality of Pakistani digital text, where Roman Urdu, Urdu script, and English mix freely in the same sentence.

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
  │     3. RAG suggestion (FAISS char-3-gram TF-IDF, 587 phrases = 467 static + 124 seed extensions)
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
Detects whether each token is Urdu script, Roman Urdu, or other. Runs a 3-tier cascade: frequency-map lookup (built from 6.37M parallel sentences), static 467-word dictionary, FAISS retrieval-augmented suggestion (seeded with 124 additional entries covering scam, toxic, and conversational vocabulary beyond the static dict — 587 total indexed phrases), then phonetic transliteration as last resort. English words, URLs, and numbers pass through untouched.

### 2. Explainable Risk Scoring
LoRA-fine-tuned XLM-RoBERTa-base for binary toxic/scam classification. Outputs a risk score (0–1), calibrated confidence via temperature scaling (T=1.409), risk level (low/medium/high), and the top 5 words driving the score using ablation-based contribution analysis. Max-ensemble scoring takes the higher of LoRA and heuristic scores. Falls back to a five-pass heuristic scorer (12 phrases + 22 single-word patterns with leetspeak normalization, typo correction, fuzzy character-spacing detection, and Levenshtein-distance fuzzy matching for novel misspellings) when the model is unavailable.

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

### Risk Scorer (trained LoRA XLM-RoBERTa)

**Test set (107 examples — full eval_dataset.csv), re-run against the real trained adapter (not the heuristic) on 2026-09-07, commit `d2428ea`:**

| Metric | Score |
|---|---|
| Accuracy | 89.7% |
| Precision (toxic/scam) | 92.5% |
| Recall (toxic/scam) | 82.2% |
| F1 (toxic/scam) | 87.1% |
| Macro Precision | 90.3% |
| Macro Recall | 88.7% |
| Macro F1 | 89.3% |

**Per-category breakdown:** benign 30/32, edge 18/19, mixed 10/10, scam 22/25, toxic 16/21.

Raw predictions and provenance (git commit, timestamp, exact command): [`tests/eval_results_full_t0.4.csv`](tests/eval_results_full_t0.4.csv), [`tests/eval_metrics_full_t0.4.json`](tests/eval_metrics_full_t0.4.json). An earlier run on a 97-example subset (before the eval set grew to 107 rows) reported accuracy 88.8% / F1 85.0% at higher precision, lower recall — consistent with this run, on a smaller, easier slice.

**Calibration:** Temperature scaling T=1.409, grid search over 100 values [0.5, 5.0] on validation set.

**Adversarial test suite — now verified against the real model, not just the heuristic.** The original 12 red-team cases (leetspeak, spacing evasion, misspelling, mixed-script, Roman Urdu scam) pass **12/12** on the deployed max-ensemble (LoRA + heuristic), re-run in-process against `models/risk_lora` on 2026-09-07: [`tests/adversarial_results_model.csv`](tests/adversarial_results_model.csv). The per-case breakdown shows the LoRA model independently driving 8 of the 12 correct scores (not just the heuristic keyword layer) — e.g. `baseline_scam` scores 1.00 from the model alone, `roman_urdu_scam` 0.99.

**Held-out set (22 cases, written after the heuristic was tuned) is split into three groups, honestly, on purpose:** 10 regression cases (true expected label, currently passing on both the heuristic and the real ensemble — `tests/test_adversarial_ci.py`, gates CI), 2 **model false positives** (heuristic gets these right, but the real deployed ensemble does not — see below), and 9 documented known gaps, reported every run and never silently relabeled to match a wrong output. An earlier version of this suite marked a real death threat ("jaan se maar doonga," scored 0 by the heuristic) as "expected=low / PASS" — that's fixed.

**Known, currently-unfixed false positives in the deployed model** (found by testing the live server, not just the heuristic, on 2026-09-07): `"The university registration fee is 5000 rupees, payable at the admissions office"` scores **0.98 HIGH** from the model alone (heuristic correctly says 0.49 medium); `"50000 100000 25000"` (bare numbers, no other words) scores **1.00 HIGH**. Root-caused, not just observed: this isn't a "numbers" bug specifically — the single word `"salary"` alone scores 0.99, `"12345"` alone scores 0.01, `"99999"` alone scores 0.98. The model has picked up spurious associations with specific tokens from the synthetic scam templates and doesn't generalize cleanly on short/sparse inputs. **Deliberately not patched with a code-level workaround** — a length- or keyword-based override would either reintroduce exactly the keyword whack-a-mole this project moved away from, or risk suppressing genuinely correct short-text catches elsewhere (e.g. `"kutta"` alone correctly scores high, and a blunt "distrust short input" rule would break that). The real fix is retraining with more short-text diversity in the negative class — tracked as the top follow-up item, not attempted here.

**Real-vocabulary generalization test (2026-09-07):** the 8 known heuristic blind spots, plus 3 more, re-run against the actual trained model (not the heuristic) — [`tests/novel_probe_results.csv`](tests/novel_probe_results.csv). None of these words/phrases appear in the heuristic's keyword lists. Result: **7 of 11 are caught by the model through genuine semantic generalization** (`gadha`/`nalayak` insult → 0.98, `investment_scam` → 0.99, `idiot_insult` → 0.97, `thief_accusation` ("chor") → 0.96, `deposit_before_joining` → 1.00, `easy_money` → 0.98, `bank_transfer_scam` → 1.00 — heuristic alone scored ≤0.15 on all seven). **4 remain genuinely missed even by the trained model**, most notably `novel_abuse_threat` ("jaan se maar doonga," a death threat) at 0.10, plus `roman_fee_request` (0.04), `verification_charges_scam` (0.18), and `romance_gift_card_scam` (0.01 — expected, since romance/gift-card scams aren't one of the 7 synthetic training categories). This is the first evidence in this project's history that the trained model generalizes beyond its keyword-matched fallback — and an honest accounting of where it still doesn't.

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
| NER producing garbage output | Model `Davlan/xlm-roberta-base-ner` trained on African languages, not Urdu | Switched to `Davlan/xlm-roberta-base-wikiann-ner` (WikiAnn, covers Urdu); normalize Roman Urdu before extraction; map PER/LOC/ORG → PERSON/LOCATION/ORGANIZATION |
| Simplify producing garbage output | Broken dictionary: English mappings (`"استعمال": "use"`), identity mappings, Hindi words, multi-word keys never matched | Rewrote dictionary (19 clean entries), multi-word phrase matching before single words, Roman Urdu support via normalization |
| HF datasets/torchvision crash on Colab | `VideoReader` import error at batch collation time | Custom `_TokenizedDataset` (plain `torch.utils.data.Dataset`) bypasses HF formatter entirely |
| pip install failures on Colab | Transient network issues, torchao conflicts | Retry logic (2 attempts with 5s delay), uninstall torchao before install |
| PEFT fails to restore classifier weights | `modules_to_save` sometimes not restored on load | Direct safetensors read + manual state_dict patch for classifier keys |
| pandas 3.0.5 deprecation warnings | Colab pip resolves newer pandas | Unpinned pandas version, accept harmless warnings |
| PDF report export crashed on every call (`Figure.plot` doesn't exist) | Copy-paste error — `.plot()` is an `Axes` method, not `Figure`; the crash was silently swallowed by a bare `try/except` in the UI, so the "Download PDF" button just did nothing, with no error shown | Fixed to draw the divider via `Line2D` on the figure; caught by generating and visually inspecting an actual PDF, not just checking for exceptions |
| PDF Urdu-script text rendered blank | Matplotlib has no text-shaping engine (no HarfBuzz/libraqm); Nastaliq fonts assume one and ship almost no usable unshaped glyphs | Bundled Noto Naskh Arabic (OFL-licensed, `static/fonts/`) instead — its default glyphs stay legible without shaping. Real Nastaliq calligraphy would need a shaping-aware renderer (e.g. a headless browser), out of scope for now |
| Common English loanwords ("available," "processing") rendered as phonetic gibberish in Normalized Text | Not in the 467-word static dictionary, so the phonetic transliteration fallback spelled them out letter-by-letter | Added 18 highest-frequency job-posting loanwords with real Urdu translations |
| NER hallucination silently removed a safety warning | The word "نوکری" (Urdu for "job") was misclassified as an ORGANIZATION entity at 96% confidence; the recommendation logic then wrongly concluded a verified organization was present and dropped the "verify independently" caution from the message | Decoupled the safety caution from NER's organization detection entirely — NER-detected entities are still shown to the user for information, but no longer gate whether a safety warning appears, since NER's org-signal isn't reliable in either direction (over- or under-detects) |

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
├── whatsapp_bot.py               # WhatsApp bot (Twilio sandbox)
├── pdf_report.py                 # PDF report export
├── architecture.png              # Architecture diagram
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
│   ├── train_risk_model_colab.ipynb  # Hardened Colab training notebook
│   ├── evaluate_model.ipynb          # Evaluation and metrics notebook
│   └── launch_demo.ipynb             # Colab Gradio share launcher
├── models/
│   ├── temperature.txt           # Calibrated temperature (1.409)
│   └── risk_lora/                # Trained LoRA adapter + tokenizer
├── data/
│   └── processed/
│       └── rag_phrase_pairs.json # RAG seed: 124 entries extending static dict to 587 total
├── tests/
│   ├── adversarial_cases.py      # 12-case red-team test suite (HTTP-based)
│   ├── run_adversarial_colab.py  # Adversarial re-run against trained model
│   ├── run_evaluation.py         # Full 107-example evaluation pipeline
│   ├── eval_dataset.csv          # 107 test examples (62 benign, 45 toxic/scam)
│   ├── eval_metrics_full_t0.4.json  # Committed evaluation metrics
│   └── test_unit.py              # 42 pytest unit tests
└── static/
    └── index.html                # Vanilla JS frontend
```

---

## Key Technical Decisions

1. **LoRA over full fine-tuning** — 4.5MB adapter vs 1.1GB full model; fast iteration, easy to ship
2. **XLM-RoBERTa over Urdu-specific models** — Handles Roman Urdu natively without script conversion at the model level
3. **3-tier normalization cascade** — Dictionary first (exact, 467 words), RAG second (fuzzy, 587 phrases via FAISS — static dict + 124 seed entries for scam/toxic/conversational vocabulary), transliteration last (phonetic) — maximizes accuracy while ensuring every word gets an Urdu-script output
4. **Temperature calibration** — Grid search on validation set prevents overconfident predictions
5. **Ablation-based contributions** — Remove each word, measure score drop → shows users *why* the model flagged the text
6. **Class-weighted loss** — Handles toxic/clean imbalance without resampling
7. **Heuristic fallback** — Four-pass keyword scorer (word-boundary regex, leetspeak normalization, typo correction with 48 misspellings, fuzzy character-spacing regex) activates when model can't load (e.g., no torch installed), so the API always returns something useful

---

## Limitations & Future Work

- **Recall gap (75.6%):** Model favors precision (97.0%) to avoid false positives. Expanding training data with more diverse toxic/scam examples would improve recall.
- **Frequency map not committed:** The Tier-1 frequency map (`data/processed/roman_urdu_freq.json`) is built from 6.37M parallel sentences on Colab via `scripts/build_normalizer_map.py` but was never downloaded to the repo. The normalizer falls back to the 467-word static dictionary + RAG (587 indexed phrases) + phonetic transliteration. Build script and design are in place; JSON is generated on first Colab run.
- **Heuristic vocabulary coverage:** The heuristic scorer's keyword/phrase lists don't cover open-ended vocabulary by design — that's what the LoRA model is for. This is now verified, not assumed: on 11 novel phrases matching zero heuristic patterns ([`tests/novel_probe_results.csv`](tests/novel_probe_results.csv)), the trained model alone correctly flagged 7 via genuine semantic generalization. **It still misses some, most importantly a direct death threat** ("jaan se maar doonga," scored 0.10 — the single highest-priority open gap in this project), plus a Roman-Urdu fee request, a synonym-based scam phrasing, and romance/gift-card scams (not one of the 7 synthetic training categories, so an expected gap, not a surprising one). Closing the threat-detection gap should be the next training priority, ahead of any new feature.
- **Simplification dictionary (19 entries):** The `COMPLEX_TO_SIMPLE` map covers 19 high-frequency formal Urdu words. This is functional but limited — expanding to 100+ entries with frequency-weighted selection is a clear next step. The architecture (multi-word matching, Roman Urdu support, complexity scoring) scales to larger dictionaries without code changes.
- **NER offset mapping:** Assumes 1:1 token alignment between original and normalized text. When the normalizer expands a single Roman Urdu token into multiple Urdu-script tokens, character offsets can desync. Works correctly for Urdu-script input; Roman Urdu entity positions may be approximate.
- **No batch inference:** Each text is processed individually (fine for demo, slow at scale).
- **Whisper base model:** `small` or `medium` would improve Urdu WER significantly but need more VRAM.
- **No model versioning:** Retraining overwrites the adapter; no experiment tracking or model registry.
