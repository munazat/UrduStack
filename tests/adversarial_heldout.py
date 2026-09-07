"""Held-out adversarial cases — written AFTER the heuristic was tuned.

These cases were NOT used during development. They test novel attacks,
boundary conditions, and false-positive risks the scorer has not been
tuned against. Results here are honest evidence, not optimized targets.

Three groups, on purpose — see tests/test_adversarial_ci.py for the full
reasoning:
- REGRESSION_CASES: true expected label, meant to pass on both the
  heuristic and the real ensemble.
- MODEL_FALSE_POSITIVES: true expected label, passes on the heuristic
  alone but is a REAL, currently-open failure on the deployed ensemble.
  Run against the live API (not the in-process heuristic-only CI check),
  this section is expected to show real FAILs — that's the point of
  running this script instead of just test_adversarial_ci.py.
- KNOWN_GAPS: true expected label, documented open gaps (never adjusted
  to match a wrong output).

Run locally (heuristic only, no live server needed):
    python tests/test_adversarial_ci.py

Run against the live API (the real deployed ensemble):
    python -m uvicorn app.main:app &   # or wherever it's actually running
    URDUSTACK_API_URL=http://127.0.0.1:8000 python tests/adversarial_heldout.py
"""

import csv
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tests.test_adversarial_ci import (
    REGRESSION_CASES,
    MODEL_FALSE_POSITIVES,
    KNOWN_GAPS,
    _check,
)

API_URL = os.getenv("URDUSTACK_API_URL", "http://localhost:8000")


def score_text(text: str):
    try:
        # 30s, not 10s: the first request after a cold server start blocks on
        # loading the LoRA model + base weights, which can take longer than
        # 10s over HTTP -- verified this caused false "FAIL"s on 2026-09-07
        # (the same cases scored correctly once the server was warm).
        resp = requests.post(
            f"{API_URL}/risk-score", json={"text": text}, timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        return (
            data.get("score", -1),
            data.get("risk_level", "error"),
            data.get("flagged_phrases", []),
            data.get("debug_scores"),
        )
    except Exception as exc:
        return -1, f"error: {exc}", [], None


def _run(cases, gate: bool):
    rows = []
    for category, desc, text, expected in cases:
        score, level, flagged, debug = score_text(text)
        ok = _check(expected, score)
        debug_str = ""
        if debug:
            lora = debug.get("lora_score")
            heur = debug.get("heuristic_score")
            method = debug.get("ensemble_method", "")
            lora_s = f"{lora:.2f}" if lora is not None else "n/a"
            debug_str = f"lora={lora_s} heur={heur:.2f} method={method}"
        status = "PASS" if ok else ("FAIL" if gate else "OPEN_GAP")
        rows.append({
            "category": category,
            "description": desc,
            "text": text,
            "expected": expected,
            "score": score,
            "predicted_level": level,
            "flagged_phrases": " | ".join(p["phrase"] for p in flagged),
            "debug_scores": debug_str,
            "gates_ci": gate,
            "status": status,
        })
        print(f"  {desc:30} expected={expected:6} score={score:.2f} level={level:6} {status}")
    return rows


def main():
    print("=== Regression suite (expected to pass on the real ensemble) ===")
    reg_rows = _run(REGRESSION_CASES, gate=True)

    print("\n=== Model false positives (expected to FAIL here -- that's the finding) ===")
    fp_rows = _run(MODEL_FALSE_POSITIVES, gate=True)

    print("\n=== Known gaps (documented, not scored as pass/fail against the demo) ===")
    gap_rows = _run(KNOWN_GAPS, gate=False)

    rows = reg_rows + fp_rows + gap_rows
    out_path = Path("tests/adversarial_results_heldout.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    reg_passed = sum(1 for r in reg_rows if r["status"] == "PASS")
    fp_failed = sum(1 for r in fp_rows if r["status"] == "FAIL")
    gap_passed = sum(1 for r in gap_rows if r["status"] == "PASS")
    print(f"\nRegression suite: {reg_passed}/{len(reg_rows)} passed.")
    print(f"Model false positives: {fp_failed}/{len(fp_rows)} confirmed still failing "
          f"(expected -- these are open, not fixed).")
    print(f"Known gaps: {gap_passed}/{len(gap_rows)} incidentally caught "
          f"(not required — tracked as open work either way).")
    print(f"Results: {out_path}")

    reg_failures = [r for r in reg_rows if r["status"] == "FAIL"]
    if reg_failures:
        print("\nUnexpected regression failures (document honestly):")
        for r in reg_failures:
            print(f"  {r['description']:30} expected={r['expected']:6} got={r['predicted_level']} score={r['score']:.2f}")

    fp_now_passing = [r for r in fp_rows if r["status"] == "PASS"]
    if fp_now_passing:
        print("\nModel false positives that are now FIXED (move these to REGRESSION_CASES):")
        for r in fp_now_passing:
            print(f"  {r['description']:30} score={r['score']:.2f}")


if __name__ == "__main__":
    main()
