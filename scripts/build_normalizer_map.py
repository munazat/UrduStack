"""
Build a Roman-Urdu -> Urdu script frequency mapping from a parallel corpus.

Supports multiple column naming conventions:
  - roman / urdu
  - Roman-Urdu text / Urdu text
  - roman_urdu / urdu_script

For each whitespace-aligned token pair, count occurrences and keep the
most frequent Urdu spelling for each Roman token.

Output: data/processed/roman_urdu_freq.json
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


_ROMAN_CANDIDATES = ["roman", "roman_urdu", "roman-urdu text", "roman text"]
_URDU_CANDIDATES = ["urdu", "urdu_script", "urdu text"]


def _resolve_column(df_columns: list[str], candidates: list[str]) -> str:
    lower_map = {c.lower().strip(): c for c in df_columns}
    for cand in candidates:
        if cand in lower_map:
            return lower_map[cand]
    raise ValueError(
        f"Could not find a column matching any of {candidates}. "
        f"Available columns: {df_columns}"
    )


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="data/raw/roman_urdu_parl.csv",
        help="Path to parallel corpus CSV with Roman-Urdu and Urdu columns.",
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
    parser.add_argument(
        "--chunk_size",
        type=int,
        default=500_000,
        help="Rows per chunk for memory-efficient processing.",
    )
    return parser.parse_args()


def build_map(path: str, min_count: int, chunk_size: int = 500_000):
    pair_counts: dict[str, Counter] = defaultdict(Counter)

    header = pd.read_csv(path, nrows=0)
    roman_col = _resolve_column(list(header.columns), _ROMAN_CANDIDATES)
    urdu_col = _resolve_column(list(header.columns), _URDU_CANDIDATES)
    print(f"Detected columns: roman='{roman_col}', urdu='{urdu_col}'")

    total_rows = 0
    skipped_rows = 0

    for chunk in pd.read_csv(path, chunksize=chunk_size, dtype=str):
        chunk = chunk[[roman_col, urdu_col]].dropna()

        roman_tokens = chunk[roman_col].str.lower().str.split()
        urdu_tokens = chunk[urdu_col].str.split()

        aligned_mask = roman_tokens.str.len() == urdu_tokens.str.len()
        roman_aligned = roman_tokens[aligned_mask]
        urdu_aligned = urdu_tokens[aligned_mask]

        skipped_rows += (~aligned_mask).sum()
        total_rows += len(chunk)

        for r_list, u_list in zip(roman_aligned, urdu_aligned):
            for r, u in zip(r_list, u_list):
                r = r.strip(".,!?؛،")
                u = u.strip()
                if r and u:
                    pair_counts[r][u] += 1

        print(f"  Processed {total_rows:,} rows ({len(pair_counts):,} unique roman tokens)...")

    print(f"Skipped {skipped_rows:,} rows with misaligned token counts.")

    mapping = {}
    for r, counter in pair_counts.items():
        if counter.total() < min_count:
            continue
        mapping[r] = counter.most_common(1)[0][0]
    return mapping


def main():
    args = parse_args()
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    mapping = build_map(args.input, args.min_count, args.chunk_size)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(mapping)} mappings to {args.output}")


if __name__ == "__main__":
    main()
