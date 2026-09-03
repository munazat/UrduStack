"""
Adversarial red-teaming cases for the risk scorer.

Run against the live API:
    python tests/adversarial_cases.py

Expected output is a CSV with each case's heuristic score. With a real model,
these same cases should be re-run and failures documented honestly.
"""

import csv
import os
import sys
from pathlib import Path

import requests

API_URL = os.getenv("URDUSTACK_API_URL", "http://localhost:8000")

CASES = [
    # category, description, text, expected_risk
    ("scam", "clean_ad", "software engineer required karachi", "low"),
    ("scam", "baseline_scam", "job available 50000 per week send processing fee", "high"),
    ("scam", "leetspeak_fee", "j0b availabl3, 50000 p3r w33k, s3nd pr0c3ssing f33", "high"),
    ("scam", "spacing_evasion", "j o b a v a i l a b l e, s e n d p r o c e s s i n g f e e", "high"),
    ("scam", "misspelling", "job availble, 50000 per wek, send procesing fee", "high"),
    ("scam", "mixed_script", "job available, 50000 per week, processing fee bhejo", "high"),
    ("scam", "roman_urdu_scam", "job hai bhai 50000 per week fee bhejo", "high"),
    ("toxic", "baseline_toxic", "kutta kamina", "high"),
    ("toxic", "leetspeak_toxic", "kutt4 k4m1n4", "high"),
    ("toxic", "spacing_toxic", "k u t t a   k a m i n a", "high"),
    ("toxic", "mixed_clean_toxic", "yar tum bohat achay ho lekin kutta", "high"),
    ("clean", "code_switch_clean", "yar aaj weather bohat achha hai", "low"),
]


def score_text(text: str):
    try:
        resp = requests.post(f"{API_URL}/risk-score", json={"text": text}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("score", -1), data.get("risk_level", "error"), data.get("flagged_phrases", [])
    except Exception as exc:
        return -1, f"error: {exc}", []


def main():
    out_path = Path("tests/adversarial_results.csv")
    rows = []
    for category, desc, text, expected in CASES:
        score, level, flagged = score_text(text)
        passed = (expected == "high" and score >= 0.4) or (expected == "low" and score < 0.4)
        rows.append({
            "category": category,
            "description": desc,
            "text": text,
            "expected": expected,
            "score": score,
            "predicted_level": level,
            "flagged_phrases": " | ".join(p["phrase"] for p in flagged),
            "passed": passed,
        })
        print(f"{desc:25} expected={expected:5} score={score:.2f} level={level} {'PASS' if passed else 'FAIL'}")

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    passed = sum(1 for r in rows if r["passed"])
    print(f"\nPassed {passed}/{total}. Results written to {out_path}")
    if passed < total:
        print("Document these failures honestly in the README/pitch.")
        sys.exit(1)


if __name__ == "__main__":
    main()
