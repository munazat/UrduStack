"""
Consume user feedback to create retraining data.

Reads data/feedback.csv (written by the /feedback API endpoint), filters
for corrections, maps labels to binary (0=clean, 1=toxic), and writes
data/feedback_retrain.csv ready for merging into the training set.

Usage:
    python scripts/consume_feedback.py
    python scripts/consume_feedback.py --merge_into data/raw/combined_risk.csv
"""

import argparse
from pathlib import Path

import pandas as pd

FEEDBACK_PATH = Path("data/feedback.csv")
OUTPUT_PATH = Path("data/feedback_retrain.csv")

LABEL_MAP = {
    "correct": None,
    "low_risk": 0,
    "medium_risk": 1,
    "high_risk": 1,
    "spam": 1,
    "not_spam": 0,
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert feedback.csv into retraining data."
    )
    parser.add_argument(
        "--feedback_path",
        default=str(FEEDBACK_PATH),
        help="Path to feedback CSV.",
    )
    parser.add_argument(
        "--output_path",
        default=str(OUTPUT_PATH),
        help="Where to write the retraining CSV.",
    )
    parser.add_argument(
        "--merge_into",
        default=None,
        help="If set, append retraining rows to this existing training CSV.",
    )
    parser.add_argument(
        "--min_confidence",
        type=float,
        default=0.5,
        help="Only use feedback where model confidence was above this threshold.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    feedback_path = Path(args.feedback_path)

    if not feedback_path.exists():
        print(f"No feedback file found at {feedback_path}. Nothing to do.")
        return

    df = pd.read_csv(feedback_path)
    print(f"Loaded {len(df)} feedback entries.")

    df = df.dropna(subset=["text", "correct_label"])
    df = df[df["correct_label"] != "correct"]
    df = df[df["confidence"] >= args.min_confidence]

    df["label"] = df["correct_label"].map(LABEL_MAP)
    df = df.dropna(subset=["label"])
    df["label"] = df["label"].astype(int)

    retrain = df[["text", "label"]].drop_duplicates(subset=["text"]).reset_index(drop=True)
    print(f"Extracted {len(retrain)} unique training samples from feedback.")

    if len(retrain) == 0:
        print("No usable feedback yet. Run the demo and collect some corrections first.")
        return

    toxic = retrain["label"].sum()
    clean = (retrain["label"] == 0).sum()
    print(f"  Toxic/spam (label=1): {toxic}")
    print(f"  Clean      (label=0): {clean}")

    retrain.to_csv(args.output_path, index=False)
    print(f"Saved to {args.output_path}")

    if args.merge_into:
        merge_path = Path(args.merge_into)
        if merge_path.exists():
            existing = pd.read_csv(merge_path)
            existing = existing[["text", "label"]]
            merged = pd.concat([existing, retrain], ignore_index=True)
            merged = merged.drop_duplicates(subset=["text"]).reset_index(drop=True)
            merged.to_csv(str(merge_path), index=False)
            print(
                f"Merged into {merge_path}: {len(existing)} + {len(retrain)} → {len(merged)} rows"
            )
        else:
            print(f"Merge target {merge_path} not found — skipping merge.")


if __name__ == "__main__":
    main()
