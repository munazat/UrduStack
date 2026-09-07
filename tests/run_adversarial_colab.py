"""Re-run the 12 adversarial cases against the trained LoRA model (max-ensemble).

Usage (in Colab, or locally with torch/transformers/peft installed):
    python tests/run_adversarial_colab.py

Produces adversarial_results_model.csv — distinct from
adversarial_results_heuristic.csv (tests/adversarial_cases.py's output,
heuristic-only). Keeping these separately named matters: a previous version
of this script wrote to the *_heuristic.csv filename despite calling the
real model, which would have silently mislabeled real-model results as
heuristic-only on the next run.
Requires: trained model in models/risk_lora/ and models/temperature.txt
"""

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CASES = [
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

THRESHOLD = 0.4


def main():
    import os
    repo_root = Path(__file__).resolve().parent.parent
    adapter_path = repo_root / "models" / "risk_lora" / "adapter_config.json"
    if not adapter_path.exists():
        print("ERROR: trained model not found at models/risk_lora/")
        print("Upload your model files first, then re-run this script.")
        sys.exit(1)

    from app.models.model_manager import get_model_manager

    manager = get_model_manager()
    print("Loading models (first run takes 30-60s)...")
    _ = manager.risk_model
    _ = manager.ner_model
    print("Models loaded.\n")

    rows = []
    for category, desc, text, expected in CASES:
        result = manager.analyze_text(text)
        score = result["risk_score"]
        level = result["risk_level"]
        flagged = [p["phrase"] for p in result.get("flagged_phrases", [])]
        debug = result.get("debug_scores") or {}

        if expected == "high":
            passed = score >= THRESHOLD
        else:
            passed = score < THRESHOLD

        rows.append({
            "category": category,
            "description": desc,
            "text": text,
            "expected": expected,
            "score": round(score, 4),
            "predicted_level": level,
            "flagged_phrases": " | ".join(flagged),
            "lora_score": debug.get("lora_score"),
            "heuristic_score": debug.get("heuristic_score"),
            "ensemble_method": debug.get("ensemble_method"),
            "passed": passed,
        })
        mark = "PASS" if passed else "FAIL"
        print(f"  {desc:25} expected={expected:5} score={score:.4f} level={level:6} {mark}")

    out_path = Path(__file__).resolve().parent / "adversarial_results_model.csv"
    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    provenance_path = Path(__file__).resolve().parent / "adversarial_results_model.provenance.txt"
    provenance_path.write_text(
        f"generated_at_utc: {datetime.now(timezone.utc).isoformat()}\n"
        f"command: python tests/run_adversarial_colab.py\n"
        f"model_path: {repo_root / 'models' / 'risk_lora'}\n",
        encoding="utf-8",
    )

    total = len(rows)
    passed_count = sum(1 for r in rows if r["passed"])
    print(f"\nPassed {passed_count}/{total}. Results written to {out_path}")

    failures = [r for r in rows if not r["passed"]]
    if failures:
        print("\nFailures:")
        for r in failures:
            print(f"  [{r['category']}] {r['description']}: "
                  f"score={r['score']:.4f}, expected={r['expected']}")
        print("\nDocument these honestly in the README/pitch.")
    else:
        print("All cases passed!")


if __name__ == "__main__":
    main()
