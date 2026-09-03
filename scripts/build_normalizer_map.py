"""
Build a Roman-Urdu -> Urdu script frequency mapping from Roman-Urdu-Parl.

Assumes the parallel corpus is a CSV with two columns: `roman` and `urdu`.
For each whitespace token pair (roman, urdu), count occurrences and keep the
most frequent Urdu spelling for each Roman token.

Output: data/processed/roman_urdu_freq.json
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="data/raw/roman_urdu_parl.csv",
        help="Path to Roman-Urdu-Parl CSV with 'roman' and 'urdu' columns.",
    )
    parser.add_argument(
        "--output",
        default="data/processed/roman_urdu_freq.json",
        help="Output JSON mapping file.",
    )
    parser.add_argument(
        "--min_count",
        type=int,
        default=2,
        help="Minimum occurrences to include a mapping.",
    )
    return parser.parse_args()


def build_map(path: str, min_count: int):
    df = pd.read_csv(path)
    required = {"roman", "urdu"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {missing}. Found: {list(df.columns)}")

    pair_counts: dict = defaultdict(Counter)
    for _, row in df.iterrows():
        roman = str(row["roman"]).split()
        urdu = str(row["urdu"]).split()
        if len(roman) != len(urdu):
            continue
        for r, u in zip(roman, urdu):
            r = r.lower().strip(".,!?؛،")
            u = u.strip()
            if r and u:
                pair_counts[r][u] += 1

    mapping = {}
    for r, counter in pair_counts.items():
        if counter.total() < min_count:
            continue
        mapping[r] = counter.most_common(1)[0][0]
    return mapping


def main():
    args = parse_args()
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    mapping = build_map(args.input, args.min_count)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(mapping)} mappings to {args.output}")


if __name__ == "__main__":
    main()
