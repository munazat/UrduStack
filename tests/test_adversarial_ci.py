"""CI-friendly adversarial held-out test — runs heuristic directly, no API needed.

Same case set as adversarial_heldout.py, calling the heuristic scorer
in-process. Used by GitHub Actions CI.

Two groups, on purpose:

- REGRESSION_CASES: "expected" is the TRUE correct label, and the system is
  currently expected to get it right. CI fails the build if any of these
  regress — this is the actual safety gate.
- KNOWN_GAPS: "expected" is ALSO the true correct label (never the system's
  wrong output) — these are documented cases the system currently fails.
  They are reported every run, loudly, but do NOT fail the build. Folding a
  known miss into the "expected" label just to make a test go green was the
  exact mistake in the previous version of this file: a real death threat
  ("jaan se maar doonga") was scored 0 and marked "expected=low / PASS".
  That made the suite report 21/21 while proving nothing about safety. This
  version reports the true pass rate on both groups, every run, so a future
  fix shows up as a gap closing instead of a graph that was always flat.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.utils.risk import compute_risk_score

# Cases the heuristic is currently expected to handle correctly.
# A regression here fails CI.
REGRESSION_CASES = [
    ("scam", "leet_spacing_combo", "pr0c3ss1ng f33 chahiye job k l1ye", "medium"),
    ("scam", "case_obfuscation", "PrOcEsSiNg FeE required for registration", "medium"),
    ("scam", "roman_advance_payment", "advance payment karo phir start karein", "medium"),
    ("clean", "legit_job_post", "We are hiring software engineers in Lahore. Apply at careers.example.com", "low"),
    ("clean", "casual_chat", "aaj mausam bohat acha hai chalo bahar chalte hain", "low"),
    ("clean", "news_headline", "Pakistan wins cricket match by 50 runs", "low"),
    ("clean", "legit_medical", "doctor ne kaha hai medicine subah shaam leni hai", "low"),
    ("edge", "empty_string", "", "low"),
    ("edge", "single_word_job", "job", "low"),
    ("edge", "url_only", "https://example.com/apply-now", "low"),
]

# Cases where the heuristic alone gets the right answer (so these pass the
# CI regression suite above) but the real deployed ensemble does not --
# verified directly against the live model, not assumed. These are NOT in
# REGRESSION_CASES because putting them there would make CI green while the
# actual deployed system is wrong on them, which is a worse kind of dishonest
# than an admitted gap. Not fixed with a quick patch on purpose: the failures
# are a single model being overconfident on short/sparse text in ways that
# don't share an identifiable pattern (e.g. "salary" alone scores 0.99,
# "12345" alone scores 0.01, "99999" alone scores 0.98 -- verified 2026-09-07).
# A length- or keyword-based override would either reintroduce the exact
# whack-a-mole pattern this suite exists to avoid, or risk suppressing
# genuinely correct short-text catches elsewhere (e.g. "kutta" alone should
# score high, and does). The real fix is retraining with more short-text
# diversity in the negative class -- tracked as future work, not attempted
# here.
MODEL_FALSE_POSITIVES = [
    ("clean", "legit_fee_context", "The university registration fee is 5000 rupees, payable at the admissions office", "medium"),  # real ensemble: 0.98 HIGH
    ("edge", "numeric_only", "50000 100000 25000", "low"),  # real ensemble: 1.00 HIGH
]

# The heuristic under-counts this (0.41, medium) since it only counts the
# pattern once regardless of repetition. The real deployed model correctly
# scores repeated slurs higher (0.99, high) -- verified 2026-09-07. Grouped
# with KNOWN_GAPS below since, like those, CI can't verify it (no GPU), but
# unlike those, the real model already closes this gap rather than leaving
# it open.

# Documented open gaps. "expected" is the TRUE real-world label (never
# adjusted to match whatever the system currently outputs). These are not
# used to fail CI — closing them is tracked work, not a silent baseline.
#
# CI runs the heuristic ONLY (compute_risk_score, no torch/transformers) —
# that's what's measured below and it's genuinely still failing these.
# But these are NOT unverified: run against the real trained model + max
# ensemble (torch/transformers/peft installed, models/risk_lora loaded —
# see tests/run_adversarial_colab.py and tests/novel_probe_results.csv,
# generated 2026-09-07), most of them are already caught by the model alone,
# via real semantic generalization, not a keyword match:
#   novel_deposit_fee       -> lora=1.00 CAUGHT (heuristic alone: 0.12, missed)
#   novel_easy_money        -> lora=0.98 CAUGHT (heuristic alone: 0.00, missed)
#   novel_bank_transfer     -> lora=1.00 CAUGHT (heuristic alone: 0.12, missed)
#   novel_abuse_idiot       -> lora=0.97 CAUGHT (heuristic alone: 0.15, missed)
#   novel_abuse_mixed (chor)-> lora=0.96 CAUGHT (heuristic alone: 0.00, missed)
# Genuinely still open even with the real model:
#   roman_fee_request       -> lora=0.04 MISSED ("bhai fee bhej do job pakki hai")
#   novel_abuse_threat      -> lora=0.10 MISSED ("jaan se maar doonga" — a death
#                              threat scored low even by the trained model; the
#                              most important open gap in this file)
#   novel_guaranteed_income -> not re-tested against the real model yet
# This heuristic-only list stays the CI baseline on purpose — CI has no GPU
# and no model weights, so it can only ever measure the fallback path. Don't
# read "OPEN GAP" below as "the product fails this" — check the notes above
# for what the real deployed ensemble actually does.
KNOWN_GAPS = [
    ("scam", "novel_deposit_fee", "pay 5000 security deposit before joining", "high"),
    ("scam", "novel_easy_money", "earn easy money daily no experience needed", "high"),
    ("scam", "novel_bank_transfer", "transfer 50000 to my easy paisa account now", "high"),
    ("scam", "novel_guaranteed_income", "guaranteed income 100000 monthly apply today", "high"),
    ("scam", "roman_fee_request", "bhai fee bhej do job pakki hai", "high"),
    ("toxic", "novel_abuse_idiot", "you are such an idiot bewaqoof", "medium"),
    ("toxic", "novel_abuse_threat", "jaan se maar doonga", "high"),
    ("toxic", "novel_abuse_mixed", "tum log sab chor ho sab k chor", "medium"),
    ("edge", "repeated_known_word", "kutta kutta kutta", "high"),
]


def _check(expected, score):
    if expected == "high":
        return score >= 0.7
    if expected == "medium":
        return 0.4 <= score < 0.7
    return score < 0.4


def _run(cases, label, gate):
    failures = 0
    for category, desc, text, expected in cases:
        score, conf, level, flagged, expl = compute_risk_score(text)
        ok = _check(expected, score)
        if not ok:
            failures += 1
        mark = "PASS" if ok else ("FAIL" if gate else "OPEN GAP")
        print(f"  {desc:30} expected={expected:6} score={score:.2f} level={level:6} {mark}")
    total = len(cases)
    print(f"\n{label}: {total - failures}/{total} passed"
          f"{'' if gate else ' (informational — does not gate CI)'}")
    return failures


def main():
    print("=== Regression suite (gates CI, heuristic-only) ===")
    reg_failures = _run(REGRESSION_CASES, "Regression suite", gate=True)

    print("\n=== Model false positives -- heuristic passes, real ensemble does NOT ===")
    print("(CI can't gate on these -- no GPU/model weights here -- but they are")
    print(" real, open failures in the deployed system. See comments above.)")
    _run(MODEL_FALSE_POSITIVES, "Model false positives", gate=False)

    print("\n=== Known gaps (tracked, does not gate CI) ===")
    _run(KNOWN_GAPS, "Known gaps", gate=False)

    if reg_failures > 0:
        print(f"\n{reg_failures} regression case(s) failed — this is a real regression.")
        sys.exit(1)
    print("\nRegression suite clean. See sections above for open work "
          "(some of it real and currently unfixed, not just theoretical).")


if __name__ == "__main__":
    main()
