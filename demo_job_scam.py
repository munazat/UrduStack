"""
Job-scam checker for Roman-Urdu job postings.

Paste a job ad and get an instant verdict: scam risk, threat type,
flagged phrases, and specific advice (e.g. "never pay upfront fees").

Run with:
    python demo_job_scam.py

This uses UrduStack's risk scoring and threat classification directly
— no API server needed.
"""

import gradio as gr

from app.utils.risk import compute_risk_score, categorize_risk


def check_posting(posting: str):
    if not posting or not posting.strip():
        return "Please paste a job posting."

    score, confidence, risk_level, flagged, explanation = compute_risk_score(posting)
    cat_result = categorize_risk(flagged)

    if score >= 0.7:
        verdict = "Likely scam / high-risk posting"
    elif score >= 0.4:
        verdict = "Some risk — review carefully before responding"
    else:
        verdict = "Looks legitimate"

    flagged_md = "\n".join(
        f"- `{p['phrase']}` (contribution: {p['contribution']:.2f})"
        for p in flagged
    )
    if not flagged_md:
        flagged_md = "_No risky phrases detected._"

    cat_labels = {
        "job_scam": "Fake Job Posting",
        "phishing": "Phishing",
        "harassment": "Harassment / Abuse",
    }
    threat_type = "None detected"
    if cat_result["categories"]:
        threat_type = ", ".join(
            cat_labels.get(c, c) for c in cat_result["categories"]
        )

    advice = cat_result.get("advice", "No specific action needed.")
    if not cat_result["categories"]:
        advice = "Standard caution applies."

    report = (
        f"## {verdict}\n\n"
        f"**Risk score:** {score:.2f} ({risk_level.upper()})  |  "
        f"**Confidence:** {confidence:.2f}\n\n"
        f"**Threat type:** {threat_type}\n\n"
        f"**Why:** {explanation}\n\n"
        f"**Flagged phrases:**\n{flagged_md}\n\n"
        f"---\n"
        f"> **Advice:** {advice}"
    )
    return report


def main():
    demo = gr.Interface(
        fn=check_posting,
        inputs=gr.Textbox(
            label="Paste a job posting",
            placeholder="Urgent hiring! Work from home, earn 50000 per week...",
            lines=8,
        ),
        outputs=gr.Markdown(label="Verdict"),
        title="Job Scam Checker — UrduStack",
        description=(
            "Paste a job ad (English, Roman Urdu, or mixed). "
            "UrduStack checks for scam patterns, classifies the threat, "
            "and gives you specific advice."
        ),
        examples=[
            ["Urgent hiring! Work from home, earn 50000 per week. Send processing fee to register."],
            ["job available, 50000 per week, send processing fee"],
            ["We are looking for a Python developer in Lahore. Please send your CV and portfolio."],
            ["data entry job 100000 per month sirf mobile se kam karein fee 5000 bhejein"],
            ["kutta kamina tu kabhi nahi sudhry ga"],
        ],
    )
    demo.launch(server_name="0.0.0.0", server_port=7861)


if __name__ == "__main__":
    main()
