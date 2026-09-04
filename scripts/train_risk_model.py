"""
LoRA fine-tune XLM-RoBERTa-base on PURUTT for toxic/scam risk scoring.

Intended to run in Google Colab free-tier GPU (T4). Assumes the PURUTT CSV
has at least the columns: `text` and `label`, where label is 1 for toxic/scam
and 0 for clean.

Outputs:
- models/risk_lora/          LoRA adapter
- models/temperature.txt     Temperature-scaling parameter from validation set
"""

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from peft import LoraConfig, TaskType, get_peft_model
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    EarlyStoppingCallback,
    Trainer,
    TrainingArguments,
    set_seed,
)


class _TokenizedDataset(torch.utils.data.Dataset):
    """Plain torch Dataset — avoids the HF datasets formatter, which on
    Colab imports torchvision.io.VideoReader at batch time and crashes.
    Each __getitem__ returns ready-to-use torch tensors."""

    def __init__(self, df, tokenizer, max_length=128):
        self.texts = df["text"].tolist()
        self.labels = df["label"].astype(int).tolist()
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        enc = self.tokenizer(
            self.texts[idx],
            padding="max_length",
            truncation=True,
            max_length=self.max_length,
        )
        return {
            "input_ids": torch.tensor(enc["input_ids"], dtype=torch.long),
            "attention_mask": torch.tensor(enc["attention_mask"], dtype=torch.long),
            "labels": torch.tensor(self.labels[idx], dtype=torch.long),
        }


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data_path",
        default="data/raw/PURUTT.csv",
        help="Path to PURUTT CSV with 'text' and 'label' columns.",
    )
    parser.add_argument(
        "--output_dir",
        default="models/risk_lora",
        help="Directory to save the LoRA adapter.",
    )
    parser.add_argument(
        "--model_name",
        default="xlm-roberta-base",
        help="Pretrained encoder to fine-tune.",
    )
    parser.add_argument(
        "--max_samples",
        type=int,
        default=100000,
        help="Max training examples (set high to use full dataset).",
    )
    parser.add_argument(
        "--val_samples",
        type=int,
        default=5000,
        help="Validation set size.",
    )
    parser.add_argument(
        "--test_samples",
        type=int,
        default=5000,
        help="Test set size.",
    )
    parser.add_argument(
        "--num_epochs",
        type=int,
        default=5,
        help="Training epochs.",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=16,
        help="Per-device batch size.",
    )
    parser.add_argument(
        "--push_to_hub",
        action="store_true",
        help="Push the adapter to the Hugging Face Hub.",
    )
    parser.add_argument(
        "--hub_model_id",
        default=None,
        help="Hub model id if pushing.",
    )
    return parser.parse_args()


def load_data(path: str, max_train: int, val: int, test: int):
    df = pd.read_csv(path)
    required = {"text", "label"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"PURUTT CSV missing columns: {missing}. Found: {list(df.columns)}")

    df = df.dropna(subset=["text", "label"]).reset_index(drop=True)

    # Coerce labels to integers. Common string labels like "0"/"1" are handled.
    try:
        df["label"] = pd.to_numeric(df["label"], errors="raise").astype(int)
    except Exception as exc:
        raise ValueError(
            "The 'label' column must contain numeric values (0 = clean, 1 = toxic/scam). "
            f"Found non-numeric values. First few labels: {df['label'].head().tolist()}"
        ) from exc

    unique_labels = set(df["label"].unique())
    if not unique_labels.issubset({0, 1}):
        raise ValueError(
            f"Labels must be 0 or 1. Found: {unique_labels}"
        )

    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    total_needed = max_train + val + test
    if len(df) < total_needed:
        if len(df) < val + test + 1:
            raise ValueError(
                f"Dataset has only {len(df)} rows — not enough for "
                f"val={val} + test={test}. Reduce --val_samples and --test_samples."
            )
        max_train = len(df) - val - test
        print(
            f"Warning: dataset has {len(df)} rows. Auto-adjusted train size to "
            f"{max_train} to leave room for val={val} and test={test}."
        )

    train = df.iloc[:max_train]
    val_df = df.iloc[max_train : max_train + val]
    test_df = df.iloc[max_train + val : max_train + val + test]
    return train, val_df, test_df


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, preds),
        "f1": f1_score(labels, preds, zero_division=0),
        "precision": precision_score(labels, preds, zero_division=0),
        "recall": recall_score(labels, preds, zero_division=0),
    }


def find_temperature(model, tokenizer, val_df, device="cuda", batch_size=256):
    """Find a single temperature parameter that minimizes NLL on validation.
    Processes data in batches to avoid OOM with large validation sets."""
    model.eval()
    texts = val_df["text"].tolist()
    labels = torch.tensor(val_df["label"].values, dtype=torch.long).to(device)

    all_logits = []
    for start in range(0, len(texts), batch_size):
        batch_texts = texts[start : start + batch_size]
        enc = tokenizer(
            batch_texts,
            padding=True,
            truncation=True,
            max_length=128,
            return_tensors="pt",
        ).to(device)
        with torch.no_grad():
            logits = model(**enc).logits
        all_logits.append(logits)

    logits = torch.cat(all_logits, dim=0)

    best_temp = 1.0
    best_nll = float("inf")
    for temp in np.linspace(0.5, 5.0, 100):
        scaled = logits / temp
        nll = torch.nn.functional.cross_entropy(scaled, labels).item()
        if nll < best_nll:
            best_nll = nll
            best_temp = temp

    return float(best_temp)


def main():
    args = parse_args()
    set_seed(42)
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    print(f"Loading data from {args.data_path}")
    train_df, val_df, test_df = load_data(
        args.data_path, args.max_samples, args.val_samples, args.test_samples
    )
    n_toxic = train_df["label"].sum()
    n_clean = len(train_df) - n_toxic
    print(
        f"Train: {len(train_df)} (toxic={n_toxic}, clean={n_clean}) | "
        f"Val: {len(val_df)} | Test: {len(test_df)}"
    )

    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    base_model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name,
        num_labels=2,
    )

    lora_config = LoraConfig(
        task_type=TaskType.SEQ_CLS,
        r=16,
        lora_alpha=32,
        lora_dropout=0.1,
        bias="none",
    )
    model = get_peft_model(base_model, lora_config)
    model.print_trainable_parameters()

    # Compute class weights to handle imbalanced datasets.
    # Weight inversely proportional to class frequency so the model
    # doesn't just predict the majority class.
    total = len(train_df)
    w_clean = total / (2.0 * max(n_clean, 1))
    w_toxic = total / (2.0 * max(n_toxic, 1))
    class_weights = torch.tensor([w_clean, w_toxic], dtype=torch.float32)
    print(f"Class weights: clean={w_clean:.3f}, toxic={w_toxic:.3f}")

    # Custom Trainer that applies class-weighted cross-entropy loss.
    class WeightedBCETrainer(Trainer):
        def __init__(self, class_weights, *a, **kw):
            super().__init__(*a, **kw)
            self.class_weights = class_weights

        def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
            labels = inputs.pop("labels")
            outputs = model(**inputs)
            logits = outputs.logits
            weight = self.class_weights.to(logits.device).to(logits.dtype)
            loss_fct = torch.nn.CrossEntropyLoss(weight=weight)
            loss = loss_fct(logits, labels)
            return (loss, outputs) if return_outputs else loss

    train_ds = _TokenizedDataset(train_df, tokenizer)
    val_ds = _TokenizedDataset(val_df, tokenizer)

    use_fp16 = torch.cuda.is_available()

    common_args = dict(
        output_dir=args.output_dir,
        num_train_epochs=args.num_epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size * 2,
        learning_rate=2e-4,
        weight_decay=0.01,
        save_strategy="epoch",
        save_total_limit=2,
        logging_strategy="steps",
        logging_steps=50,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        seed=42,
        report_to="none",
        push_to_hub=args.push_to_hub,
        hub_model_id=args.hub_model_id,
        fp16=use_fp16,
    )
    try:
        training_args = TrainingArguments(eval_strategy="epoch", **common_args)
    except TypeError:
        training_args = TrainingArguments(evaluation_strategy="epoch", **common_args)

    try:
        trainer = WeightedBCETrainer(
            class_weights=class_weights,
            model=model,
            args=training_args,
            train_dataset=train_ds,
            eval_dataset=val_ds,
            processing_class=tokenizer,
            compute_metrics=compute_metrics,
            callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
        )
    except TypeError:
        trainer = WeightedBCETrainer(
            class_weights=class_weights,
            model=model,
            args=training_args,
            train_dataset=train_ds,
            eval_dataset=val_ds,
            tokenizer=tokenizer,
            compute_metrics=compute_metrics,
            callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
        )

    trainer.train()

    print("Saving adapter...")
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    print(f"Calibrating temperature on validation set (device={device})...")
    temperature = find_temperature(model, tokenizer, val_df, device=device)
    temp_path = Path(args.output_dir).parent / "temperature.txt"
    temp_path.write_text(str(temperature))
    print(f"Temperature saved to {temp_path}: {temperature:.4f}")

    if test_df is not None and len(test_df) > 0:
        print("Evaluating on test set...")
        test_ds = _TokenizedDataset(test_df, tokenizer)
        metrics = trainer.evaluate(test_ds)
        print(metrics)


if __name__ == "__main__":
    main()
