import gradio as gr


def _naive_keyword_score(text: str) -> dict:
    """Baseline: exact English keyword matching only.
    No normalization, no model, no code-switching awareness."""
    from app.utils.risk import HIGH_RISK_PATTERNS

    lower = text.lower()
    matched = []
    total = 0.0
    for phrase, weight in HIGH_RISK_PATTERNS.items():
        if phrase in lower:
            matched.append(phrase)
            total += weight

    score = min(round(total, 2), 0.99)
    predicted = "toxic/scam" if score >= 0.3 else "clean"
    return {
        "score": score,
        "predicted": predicted,
        "matched_keywords": matched,
        "method": "Keyword matching (English only)",
    }


def comparison_analysis(text: str):
    """Run naive baseline + full UrduStack pipeline side by side."""
    if not text or not text.strip():
        return "Please enter some text.", "", ""

    naive = _naive_keyword_score(text)

    from app.models.model_manager import get_model_manager
    manager = get_model_manager()
    full = manager.analyze_text(text)

    naive_report = _build_naive_report(naive)
    full_report = _build_report(full)
    verdict = _build_verdict(naive, full)
    return naive_report, full_report, verdict


def _build_naive_report(naive: dict) -> str:
    """Format the naive keyword baseline result as markdown."""
    icon = "\U0001f534" if naive["predicted"] == "toxic/scam" else "\U0001f7e2"
    lines = [
        f"## {icon} Naive Baseline: {naive['predicted'].upper()}",
        f"**Score:** {naive['score']:.2f}  |  **Method:** {naive['method']}",
        "",
    ]
    if naive["matched_keywords"]:
        lines.append("### Matched Keywords")
        for kw in naive["matched_keywords"]:
            lines.append(f"- `{kw}`")
    else:
        lines.append("*No keywords matched.*")
    return "\n".join(lines)


def _build_verdict(naive: dict, full: dict) -> str:
    """Build a comparison verdict showing where UrduStack adds value."""
    naive_label = naive["predicted"]
    full_label = "toxic/scam" if full["risk_level"] in ("high", "medium") else "clean"
    agree = naive_label == full_label

    lines = ["## Verdict", ""]
    lines.append(f"| | Naive Baseline | UrduStack |")
    lines.append(f"|---|---|---|")
    lines.append(f"| **Prediction** | {naive_label} | {full_label} |")
    lines.append(f"| **Score** | {naive['score']:.2f} | {full['risk_score']:.2f} |")
    lines.append("")

    if agree:
        lines.append("Both methods agree on this input.")
    else:
        if full_label == "toxic/scam" and naive_label == "clean":
            lines.append(
                "**UrduStack caught risky content the naive baseline missed.** "
                "This is the value of normalization + fine-tuned model: "
                "it understands Roman Urdu, code-switched text, and context "
                "that simple English keyword matching cannot."
            )
        else:
            lines.append(
                "The methods disagree. The full pipeline has additional context "
                "from normalization and entity recognition to make a more "
                "informed decision."
            )

    if full.get("entities"):
        lines.append("")
        lines.append(f"**Entities found:** {len(full['entities'])} "
                     f"(naive baseline: 0 — no NER capability)")

    return "\n".join(lines)


def _build_report(result: dict) -> str:
    """Build a unified markdown report from the full analysis pipeline."""
    lines = []

    risk_emoji = {"high": "\U0001f534", "medium": "\U0001f7e0", "low": "\U0001f7e2"}
    risk_icon = risk_emoji.get(result["risk_level"], "")

    lines.append(f"## {risk_icon} Risk: {result['risk_level'].upper()}")
    lines.append(
        f"**Score:** {result['risk_score']:.2f}  |  "
        f"**Confidence:** {result['risk_confidence']:.2f}"
    )
    lines.append("")

    if result.get("entities"):
        lines.append("### Entities Detected")
        icon_map = {
            "PERSON": "\U0001f464",
            "LOCATION": "\U0001f4cd",
            "ORGANIZATION": "\U0001f3e2",
            "DATE": "\U0001f4c5",
            "MISC": "\U0001f3f7\ufe0f",
        }
        for e in result["entities"]:
            icon = icon_map.get(e["entity_group"], "\U0001f3f7\ufe0f")
            lines.append(
                f"{icon} **{e['word']}** \u2014 {e['entity_group']} "
                f"({e['score']:.2f})"
            )
        lines.append("")

    if result.get("entity_context"):
        lines.append("### Entity Context")
        for ctx in result["entity_context"]:
            lines.append(f"- {ctx}")
        lines.append("")

    if result.get("flagged_phrases"):
        lines.append("### Flagged Phrases")
        for p in result["flagged_phrases"][:5]:
            lines.append(
                f"- `{p['phrase']}` (contribution: {p['contribution']:.2f})"
            )
        lines.append("")

    lines.append("### Explanation")
    lines.append(result["explanation"])
    lines.append("")

    simplified = result.get("simplified_explanation", "")
    if simplified and simplified != result["explanation"]:
        lines.append("### Plain Language")
        lines.append(simplified)
        lines.append("")

    lines.append(f"> **Recommendation:** {result.get('recommendation', '')}")

    return "\n".join(lines)


def unified_text_analysis(text: str):
    """Run the full pipeline on text input."""
    if not text or not text.strip():
        return "Please enter some text to analyze.", ""

    from app.models.model_manager import get_model_manager

    manager = get_model_manager()
    result = manager.analyze_text(text)

    report = _build_report(result)
    normalized = result["normalized"]
    norm_header = (
        f"Normalized (confidence {result['norm_confidence']:.2f}):\n{normalized}"
    )
    return report, norm_header


def unified_audio_analysis(audio_path):
    """Transcribe audio, then run the full pipeline."""
    if audio_path is None:
        return "Please record or upload audio.", ""

    from app.utils.transcription import transcribe_audio_path
    from app.models.model_manager import get_model_manager

    text, speech_conf = transcribe_audio_path(audio_path)
    if not text:
        return "Could not transcribe audio. Try speaking more clearly.", ""

    manager = get_model_manager()
    result = manager.analyze_text(text)

    report = _build_report(result)
    transcript_info = (
        f"**Transcription** (confidence {speech_conf:.2f}):\n\n{text}\n\n"
        f"**Normalized:** {result['normalized']}"
    )
    return report, transcript_info


def build_demo() -> gr.Blocks:
    with gr.Blocks(
        title="UrduStack \u2014 Unified Urdu NLP Analysis",
        theme=gr.themes.Soft(),
    ) as demo:
        gr.Markdown(
            "# UrduStack\n"
            "Unified Urdu NLP infrastructure: normalization, risk scoring, "
            "entity recognition, and plain-language explanations \u2014 "
            "all in one pipeline."
        )

        with gr.Tabs():
            with gr.Tab("Text Analysis"):
                text_input = gr.Textbox(
                    label="Input (Urdu / Roman Urdu / English mix)",
                    placeholder="yar bhai I'm bohat pareshan aaj...",
                    lines=3,
                )
                text_btn = gr.Button("Analyze", variant="primary")
                text_report = gr.Markdown(label="Analysis Report")
                text_norm = gr.Markdown(label="Normalized Text")

                text_btn.click(
                    unified_text_analysis,
                    inputs=[text_input],
                    outputs=[text_report, text_norm],
                )

                gr.Examples(
                    examples=[
                        ["yar mujhe pareshan mat karo bro"],
                        ["job available, 50000 per week, send processing fee"],
                        ["Imran Khan ne Lahore mein PTI ki rally ki"],
                        ["bhai ye to scam lag raha hai, paise mat bhejo"],
                        ["free iphone jeetny k liye link click karein"],
                        [
                            "\u062d\u06a9\u0648\u0645\u062a \u0646\u06d2 "
                            "\u0636\u0631\u0648\u0631\u06cc \u062a\u0639\u0644\u06cc\u0645 "
                            "\u06a9\u06d2 \u0644\u06cc\u06d2 \u0646\u0626\u06cc "
                            "\u0645\u0639\u0644\u0648\u0645\u0627\u062a \u062c\u0627\u0631\u06cc \u06a9\u06cc"
                        ],
                    ],
                    inputs=[text_input],
                )

            with gr.Tab("Speech Analysis"):
                audio_input = gr.Audio(
                    label="Record or upload Urdu audio",
                    type="filepath",
                )
                audio_btn = gr.Button(
                    "Transcribe & Analyze", variant="primary"
                )
                audio_report = gr.Markdown(label="Analysis Report")
                audio_transcript = gr.Markdown(label="Transcription")

                audio_btn.click(
                    unified_audio_analysis,
                    inputs=[audio_input],
                    outputs=[audio_report, audio_transcript],
                )

            with gr.Tab("Comparison"):
                gr.Markdown(
                    "### Naive Keyword Baseline vs. UrduStack\n"
                    "See how simple English keyword matching fails on "
                    "Roman Urdu, code-switched text, and context — "
                    "while the full UrduStack pipeline catches it."
                )
                comp_input = gr.Textbox(
                    label="Input (try Roman Urdu scam or toxic text)",
                    placeholder="free iphone jeetny k liye link click karein",
                    lines=3,
                )
                comp_btn = gr.Button("Compare", variant="primary")

                with gr.Row():
                    comp_naive = gr.Markdown(label="Naive Baseline")
                    comp_full = gr.Markdown(label="UrduStack Full Pipeline")

                comp_verdict = gr.Markdown(label="Verdict")

                comp_btn.click(
                    comparison_analysis,
                    inputs=[comp_input],
                    outputs=[comp_naive, comp_full, comp_verdict],
                )

                gr.Examples(
                    examples=[
                        ["free iphone jeetny k liye link click karein"],
                        ["bhai ye to scam lag raha hai, paise mat bhejo"],
                        ["job available, 50000 per week, send processing fee"],
                        ["tumhara account block ho gaya hai, abhi call karein"],
                        ["yar normal baat hai, koi tension nahi"],
                        ["send money now or your account will be blocked"],
                    ],
                    inputs=[comp_input],
                )

        gr.Markdown(
            "---\n"
            "**Pipeline:** Normalize \u2192 Risk Score \u2192 "
            "Entity Recognition \u2192 Context Enrichment \u2192 "
            "Simplify \u2192 Recommendation"
        )

    return demo


def main():
    demo = build_demo()
    demo.launch(server_name="0.0.0.0", server_port=7860)


if __name__ == "__main__":
    main()
