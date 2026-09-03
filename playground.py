import os
import requests
import gradio as gr

API_URL = os.getenv("URDUSTACK_API_URL", "http://localhost:8000")


def analyze(text: str):
    if not text or not text.strip():
        return "", "", "Please enter some text."

    norm_resp = requests.post(
        f"{API_URL}/normalize", json={"text": text}, timeout=30
    )
    norm_resp.raise_for_status()
    norm = norm_resp.json()

    risk_resp = requests.post(
        f"{API_URL}/risk-score", json={"text": text}, timeout=30
    )
    risk_resp.raise_for_status()
    risk = risk_resp.json()

    normalized = norm.get("normalized", "")
    confidence = norm.get("confidence", 0.0)

    score = risk.get("score", 0.0)
    rconf = risk.get("confidence", 0.0)
    level = risk.get("risk_level", "unknown")
    explanation = risk.get("explanation", "")
    flagged = risk.get("flagged_phrases", [])

    flagged_text = "\n".join(
        f"- `{p['phrase']}` (contribution {p['contribution']:.2f})"
        for p in flagged
    )
    if not flagged_text:
        flagged_text = "No phrases flagged."

    summary = (
        f"**Risk level:** {level.upper()}\n\n"
        f"**Score:** {score:.2f} | **Confidence:** {rconf:.2f}\n\n"
        f"**Explanation:** {explanation}\n\n"
        f"**Normalized text** (confidence {confidence:.2f}):\n{normalized}\n\n"
        f"**Flagged phrases:**\n{flagged_text}"
    )
    return normalized, f"{score:.2f}", summary


def main():
    demo = gr.Interface(
        fn=analyze,
        inputs=gr.Textbox(
            label="Input (Urdu / Roman Urdu / English mix)",
            placeholder="yar bhai I'm bohat pareshan aaj...",
            lines=3,
        ),
        outputs=[
            gr.Textbox(label="Normalized Urdu", interactive=False),
            gr.Textbox(label="Risk Score", interactive=False),
            gr.Markdown(label="Analysis"),
        ],
        title="UrduStack Playground",
        description=(
            "Type mixed-script Urdu text and see the normalized output "
            "plus an explainable risk/toxicity score."
        ),
        examples=[
            ["yar mujhe pareshan mat karo bro"],
            ["job available, 50000 per week, send processing fee"],
            ["aaj weather bohat achha hai"],
        ],
    )
    demo.launch(server_name="0.0.0.0", server_port=7860)


if __name__ == "__main__":
    main()
