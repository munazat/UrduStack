"""
Job-scam checker demo built on top of UrduStack.

Run with:
    python demo_job_scam.py

Paste a job posting and see the normalized Urdu text + scam risk verdict
with highlighted risky phrases.
"""

import os

import gradio as gr
import requests

API_URL = os.getenv("URDUSTACK_API_URL", "http://localhost:8000")


def check_posting(posting: str):
    if not posting or not posting.strip():
        return "", "Please paste a job posting."

    norm_resp = requests.post(
        f"{API_URL}/normalize", json={"text": posting}, timeout=30
    )
    norm_resp.raise_for_status()
    normalized = norm_resp.json()["normalized"]

    risk_resp = requests.post(
        f"{API_URL}/risk-score", json={"text": posting}, timeout=30
    )
    risk_resp.raise_for_status()
    risk = risk_resp.json()

    score = risk.get("score", 0.0)
    level = risk.get("risk_level", "unknown")
    explanation = risk.get("explanation", "")
    flagged = risk.get("flagged_phrases", [])

    if score >= 0.7:
        verdict = "⚠️ Likely scam / high-risk posting"
    elif score >= 0.4:
        verdict = "⚡ Some risk — review carefully"
    else:
        verdict = "✅ Looks legitimate"

    flagged_md = "\n".join(
        f"- `{p['phrase']}` (contribution {p['contribution']:.2f})"
        for p in flagged
    )
    if not flagged_md:
        flagged_md = "_No risky phrases detected._"

    report = (
        f"## {verdict}\n\n"
        f"**Risk score:** {score:.2f} ({level.upper()})\n\n"
        f"**Why:** {explanation}\n\n"
        f"**Normalized text:**\n{normalized}\n\n"
        f"**Flagged phrases:**\n{flagged_md}\n\n"
        f"---\n"
        f"_Demo built with UrduStack in ~2 hours._"
    )
    return normalized, report


def main():
    demo = gr.Interface(
        fn=check_posting,
        inputs=gr.Textbox(
            label="Job posting",
            placeholder="Paste the job ad here...",
            lines=8,
        ),
        outputs=[
            gr.Textbox(label="Normalized Urdu", interactive=False),
            gr.Markdown(label="Verdict"),
        ],
        title="Job Scam Checker",
        description="A tiny demo app built on the UrduStack API.",
        examples=[
            ["Urgent hiring! Work from home, earn 50000 per week. Send processing fee to register."],
            ["We are looking for a Python developer in Lahore. Please send your CV and portfolio."],
        ],
    )
    demo.launch(server_name="0.0.0.0", server_port=7861)


if __name__ == "__main__":
    main()
