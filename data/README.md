# Datasets

This folder holds the datasets used by UrduStack.

## Required datasets

| Dataset | File | Columns | Purpose |
|---|---|---|---|
| PURUTT | `data/raw/PURUTT.csv` | `text`, `label` | Toxic/scam classification |
| Roman-Urdu-Parl | `data/raw/roman_urdu_parl.csv` | `roman`, `urdu` | Transliteration mapping |
| UrduSpeech | `data/raw/urdu_speech/` | audio + transcripts | Speech-to-text evaluation |

## Setup

1. Download the datasets manually (the prompt says not to download them during a Qoder run).
2. Place them in `data/raw/` with the filenames above.
3. Run `python scripts/build_normalizer_map.py` to generate `data/processed/roman_urdu_freq.json`.
4. Run `python scripts/train_risk_model.py` in Colab or locally to train the risk-scoring adapter.

## Processed outputs

- `data/processed/roman_urdu_freq.json` — frequency-derived Roman-Urdu → Urdu mapping
