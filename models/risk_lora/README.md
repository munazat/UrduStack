---
base_model: xlm-roberta-base
library_name: peft
tags:
- base_model:adapter:xlm-roberta-base
- lora
- transformers
- text-classification
- toxic-detection
- scam-detection
- urdu
- roman-urdu
- code-switching
- multilingual
license: mit
---

# UrduStack Risk LoRA Adapter

LoRA adapter fine-tuned on XLM-RoBERTa-base for binary toxic/scam
classification of Urdu, Roman Urdu, and English code-switched text.

## Model Details

- **Developed by:** Munaza Tariq, Shahoud Shahid
- **Model type:** LoRA adapter (PEFT) on XLM-RoBERTa-base
- **Task:** Binary sequence classification (toxic/scam vs. clean)
- **Languages:** Urdu (Nastaliq script), Roman Urdu (Latin transliteration),
  English, and code-switched mixtures of all three
- **License:** MIT
- **Base model:** [`xlm-roberta-base`](https://huggingface.co/xlm-roberta-base)

## Uses

### Direct Use

Load with PEFT and classify text as risky or clean:

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from peft import PeftModel

base = "xlm-roberta-base"
tokenizer = AutoTokenizer.from_pretrained(base)
model = AutoModelForSequenceClassification.from_pretrained(base, num_labels=2)
model = PeftModel.from_pretrained(model, "models/risk_lora")

import torch
inputs = tokenizer("free iphone jeetny k liye link click karein",
                    return_tensors="pt", truncation=True, max_length=128)
with torch.no_grad():
    logits = model(**inputs).logits
    temperature = 1.4090909090909092
    probs = torch.softmax(logits / temperature, dim=-1)
    risk_prob = probs[0, 1].item()
    label = "risky" if risk_prob >= 0.3 else "clean"
    print(f"{label} (score={risk_prob:.2f})")
```

### Out-of-Scope Use

This model is not designed for:
- Multilabel classification (only binary: risky vs. clean)
- Languages other than Urdu, Roman Urdu, and English
- Long documents (>128 tokens are truncated)

## Training Details

### Training Data

- **PURUTT** (Roman-Urdu-Toxic-Corpus): 72,700 labeled Roman Urdu
  samples from [`hafiz-hassaan-saeed/Roman-Urdu-Toxic-Corpus`](https://huggingface.co/datasets/hafiz-hassaan-saeed/Roman-Urdu-Toxic-Corpus)
  (CC-BY-4.0).
- **Synthetic scam data**: 500 rule-generated Roman Urdu scam messages
  covering job scams, lottery fraud, phishing, and fee fraud patterns.

### Training Hyperparameters

| Parameter | Value |
|---|---|
| LoRA rank (r) | 16 |
| LoRA alpha | 32 |
| LoRA dropout | 0.1 |
| Target modules | query, value |
| Modules saved | classifier, score |
| Task type | SEQ_CLS |
| Learning rate | 2e-4 |
| Epochs | 5 |
| Batch size | 32 |
| Weight decay | 0.01 |
| Class weights | balanced (inverse frequency) |
| Early stopping | patience=3, metric=val_f1 |

### Training Infrastructure

- **Hardware:** NVIDIA T4 GPU (Google Colab free tier)
- **Framework:** PEFT 0.20.0, Transformers 4.49+, PyTorch 2.x

## Evaluation

### Metrics

Evaluated on a held-out 20% test split from PURUTT + synthetic scam data.

| Metric | Value |
|---|---|
| **Accuracy** | 88.8% |
| **Precision** | 97.0% |
| **Recall** | 75.6% |
| **F1** | 85.0% |

### Calibration

Raw logits are scaled by a learned temperature parameter
**T = 1.41** before softmax, improving confidence calibration.
The classification threshold is set at **0.30** (risk probability
above 0.30 is flagged as risky) to prioritize recall on toxic content
while keeping precision high.

## Bias, Risks, and Limitations

- **Recall gap:** Recall (75.6%) is lower than precision (97.0%).
  Some toxic content will be missed — the model favors precision
  to avoid false positives.
- **Character-spaced evasion:** Adversaries who space out individual
  characters ("k u t t a") can bypass detection. A preprocessing
  collapse step mitigates this but is not foolproof.
- **Domain shift:** Trained on social media text. Performance may
  degrade on formal Urdu, literary text, or domain-specific jargon.
- **No context window:** Single-turn classification only. Does not
  consider conversation history or user intent.

## Environmental Impact

- **Hardware:** NVIDIA T4 (Google Colab)
- **Training time:** ~2 hours
- **Carbon emitted:** Negligible (single GPU, short training run)

## Model Card Authors

Munaza Tariq, Shahoud Shahid
