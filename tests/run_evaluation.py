"""Run the full evaluation dataset through the trained pipeline.

Usage (in Colab after uploading model):
    python tests/run_evaluation.py
    python tests/run_evaluation.py --mode adversarial   # original 12 only
    python tests/run_evaluation.py --mode full          # all 97 examples

Requires: trained model in models/risk_lora/ and models/temperature.txt
"""

import csv
import os
import sys
import time
from pathlib import Path

from sklearn.metrics import (
    precision_recall_fscore_support,
    accuracy_score,
    classification_report,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent

THRESHOLD = 0.4
ADVERSARIAL_DESCRIPTIONS = {
    "clean_ad", "baseline_scam", "leetspeak_fee", "spacing_evasion",
    "misspelling_adv", "mixed_script", "roman_urdu_scam",
    "baseline_toxic", "leetspeak_toxic", "spacing_toxic",
    "mixed_clean_toxic", "code_switch_clean",
}


def load_dataset(mode="full"):
    path = TESTS_DIR / "eval_dataset.csv"
    if not path.exists():
        print(f"ERROR: {path} not found")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if mode == "adversarial":
        filtered = [r for r in rows if r.get("description") in ADVERSARIAL_DESCRIPTIONS]
        print(
            f"Loaded {len(filtered)}/{len(rows)} adversarial cases "
            f"from {path}"
        )
        return filtered

    print(f"Loaded {len(rows)} examples from {path}")
    return rows


def main():
    mode = "full"
    for arg in sys.argv[1:]:
        if arg == "--mode":
            continue
        if arg in ("full", "adversarial"):
            mode = arg

    examples = load_dataset(mode)

    if not os.path.exists(REPO_ROOT / "models" / "risk_lora" / "adapter_config.json"):
        print("ERROR: trained model not found at models/risk_lora/")
        print("Upload your model files first.")
        sys.exit(1)

    from app.models.model_manager import get_model_manager

    manager = get_model_manager()
    print("Loading models (first run takes 30-60s)...")
    _ = manager.risk_model
    print("Risk model loaded.")
    _ = manager.ner_model
    print("NER model loaded.")
    print()

    results = []
    errors = 0

    for i, example in enumerate(examples):
        text = example["text"]
        expected = int(example["expected_label"])
        category = example["category"]
        description = example.get("description", "")

        try:
            result = manager.analyze_text(text)
            score = result["risk_score"]
            confidence = result["risk_confidence"]
            risk_level = result["risk_level"]
            predicted = 1 if score >= THRESHOLD else 0
            correct = predicted == expected
            flagged = [p["phrase"] for p in result.get("flagged_phrases", [])]
            entities = [e["word"] for e in result.get("entities", [])]
            explanation = result.get("explanation", "")

            if not correct:
                errors += 1

            results.append(
                {
                    "text": text,
                    "expected_label": expected,
                    "predicted_label": predicted,
                    "correct": correct,
                    "risk_score": round(score, 4),
                    "confidence": round(confidence, 4),
                    "risk_level": risk_level,
                    "flagged_phrases": " | ".join(flagged),
                    "entities": " | ".join(entities),
                    "category": category,
                    "description": description,
                    "explanation": explanation,
                }
            )

            mark = "PASS" if correct else "FAIL"
            print(
                f"  [{i + 1:3}/{len(examples)}] {mark}  "
                f"score={score:.2f}  exp={expected} pred={predicted}  "
                f"{category}/{description}"
            )

        except Exception as e:
            errors += 1
            results.append(
                {
                    "text": text,
                    "expected_label": expected,
                    "predicted_label": -1,
                    "correct": False,
                    "risk_score": -1,
                    "confidence": -1,
                    "risk_level": "error",
                    "flagged_phrases": "",
                    "entities": "",
                    "category": category,
                    "description": description,
                    "explanation": f"ERROR: {e}",
                }
            )
            print(
                f"  [{i + 1:3}/{len(examples)}] ERR   {category}/{description}: {e}"
            )

    total = len(results)
    passed = total - errors
    print(f"\nCompleted: {passed}/{total} correct")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    y_true = [r["expected_label"] for r in results]
    y_pred = [max(0, r["predicted_label"]) for r in results]

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", pos_label=1
    )
    accuracy = accuracy_score(y_true, y_pred)

    print(f"\n  Accuracy (all classes):  {accuracy:.4f}")
    print(f"  Toxic/Scam class:")
    print(f"    Precision:             {precision:.4f}")
    print(f"    Recall:                {recall:.4f}")
    print(f"    F1:                    {f1:.4f}")

    macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro"
    )
    print(f"\n  Macro avg:")
    print(f"    Precision:             {macro_p:.4f}")
    print(f"    Recall:                {macro_r:.4f}")
    print(f"    F1:                    {macro_f1:.4f}")

    try:
        print("\n" + classification_report(
            y_true, y_pred, labels=[0, 1],
            target_names=["clean", "toxic/scam"],
            zero_division=0,
        ))
    except ValueError as e:
        print(f"\n(classification_report skipped: {e})")

    print("Per-category breakdown:")
    categories = sorted(set(r["category"] for r in results))
    for cat in categories:
        cat_results = [r for r in results if r["category"] == cat]
        cat_passed = sum(1 for r in cat_results if r["correct"])
        print(f"  {cat:12}: {cat_passed}/{len(cat_results)}")

    failures = [r for r in results if not r["correct"]]
    if failures:
        print("\n" + "=" * 70)
        print("FAILURES")
        print("=" * 70)
        for r in failures:
            exp_str = "toxic/scam" if r["expected_label"] == 1 else "clean"
            pred_str = "toxic/scam" if r["predicted_label"] == 1 else "clean"
            if r["predicted_label"] == -1:
                pred_str = "ERROR"
            print(f"\n  [{r['category']}] {r['description']}")
            print(f"    Text:      {r['text']}")
            print(f"    Expected:  {exp_str}")
            print(f"    Predicted: {pred_str} (score={r['risk_score']:.2f})")
            if r["flagged_phrases"]:
                print(f"    Flagged:   {r['flagged_phrases']}")

    results_path = TESTS_DIR / f"eval_results_{mode}.csv"
    fieldnames = list(results[0].keys())
    with open(results_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    metrics_path = TESTS_DIR / f"eval_metrics_{mode}.json"
    import json

    metrics = {
        "mode": mode,
        "total": total,
        "passed": passed,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "macro_precision": round(macro_p, 4),
        "macro_recall": round(macro_r, 4),
        "macro_f1": round(macro_f1, 4),
        "per_category": {
            cat: {
                "total": len([r for r in results if r["category"] == cat]),
                "passed": sum(1 for r in results if r["category"] == cat and r["correct"]),
            }
            for cat in categories
        },
    }
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to {results_path}")
    print(f"Metrics saved to {metrics_path}")


if __name__ == "__main__":
    main()
