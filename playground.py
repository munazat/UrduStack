import gradio as gr

from app.models.risk_model import RiskModel
from app.utils.normalization import normalize_with_segments

_risk_model = RiskModel()


def analyze(text: str):
    if not text or not text.strip():
        return "", "", "Please enter some text."

    normalized, confidence, _segments = normalize_with_segments(text)
    score, rconf, risk_level, flagged_phrases, explanation = _risk_model.score(text)

    flagged_text = "\n".join(
        f"- `{p['phrase']}` (contribution {p['contribution']:.2f})"
        for p in flagged_phrases
    )
    if not flagged_text:
        flagged_text = "No phrases flagged."

    summary = (
        f"**Risk level:** {risk_level.upper()}\n\n"
        f"**Score:** {score:.2f} | **Confidence:** {rconf:.2f}\n\n"
        f"**Explanation:** {explanation}\n\n"
        f"**Normalized text** (confidence {confidence:.2f}):\n{normalized}\n\n"
        f"**Flagged phrases:**\n{flagged_text}"
    )
    return normalized, f"{score:.2f}", summary


def find_entities(text: str):
    if not text or not text.strip():
        return "Please enter some text."

    from app.models.ner_model import get_ner_model

    entities = get_ner_model().extract_entities(text)
    if not entities:
        return "No entities found."

    lines = []
    for e in entities:
        icon = {"PERSON": "👤", "LOCATION": "📍", "ORGANIZATION": "🏢",
                "DATE": "📅", "MISC": "🏷️"}.get(
            e["entity_group"], "🏷️"
        )
        lines.append(
            f"{icon} **{e['word']}** — {e['entity_group']} "
            f"(confidence {e['score']:.2f})"
        )
    return "\n\n".join(lines)


def simplify_text(text: str):
    if not text or not text.strip():
        return "", "Please enter some text."

    from app.utils.simplify import simplify, get_vocabulary_level

    simplified, changes = simplify(text)
    level = get_vocabulary_level(text)

    if not changes:
        return simplified, "No complex words found. Text is already simple."

    lines = [f"**Simplified {len(changes)} word(s):**\n"]
    for c in changes:
        lines.append(f"- `{c['original']}` → **{c['simplified']}**")
    lines.append(
        f"\n**Complexity:** {level['complex_words']}/{level['total_words']} words "
        f"({level['complexity_ratio']*100:.0f}% complex)"
    )
    return simplified, "\n".join(lines)


def transcribe_and_analyze(audio_path):
    if audio_path is None:
        return "", "", "Please record or upload audio.", ""

    from app.utils.transcription import transcribe_audio_path

    text, conf = transcribe_audio_path(audio_path)
    if not text:
        return "", "", "Could not transcribe audio. Try speaking more clearly.", ""

    normalized, norm_conf, _segments = normalize_with_segments(text)
    score, rconf, risk_level, flagged_phrases, explanation = _risk_model.score(text)

    flagged_text = "\n".join(
        f"- `{p['phrase']}` (contribution {p['contribution']:.2f})"
        for p in flagged_phrases
    )
    if not flagged_text:
        flagged_text = "No phrases flagged."

    summary = (
        f"**Risk level:** {risk_level.upper()}\n\n"
        f"**Score:** {score:.2f} | **Confidence:** {rconf:.2f}\n\n"
        f"**Explanation:** {explanation}\n\n"
        f"**Flagged phrases:**\n{flagged_text}"
    )
    return text, normalized, summary, f"Speech confidence: {conf:.2f}"


def main():
    with gr.Blocks(
        title="UrduStack — Code-Switch-Aware Urdu NLP",
        theme=gr.themes.Soft(),
    ) as demo:
        gr.Markdown(
            "# UrduStack\n"
            "Code-switch-aware Urdu NLP: normalization, risk scoring, "
            "and speech-to-text in one pipeline."
        )

        with gr.Tabs():
            with gr.Tab("Text Analysis"):
                text_input = gr.Textbox(
                    label="Input (Urdu / Roman Urdu / English mix)",
                    placeholder="yar bhai I'm bohat pareshan aaj...",
                    lines=3,
                )
                text_btn = gr.Button("Analyze", variant="primary")
                with gr.Row():
                    norm_out = gr.Textbox(label="Normalized Urdu", interactive=False)
                    score_out = gr.Textbox(label="Risk Score", interactive=False)
                analysis_out = gr.Markdown(label="Analysis")
                text_btn.click(
                    analyze,
                    inputs=[text_input],
                    outputs=[norm_out, score_out, analysis_out],
                )

            with gr.Tab("Speech-to-Text"):
                audio_input = gr.Audio(
                    label="Record or upload Urdu audio",
                    type="filepath",
                )
                audio_btn = gr.Button("Transcribe & Analyze", variant="primary")
                transcript_out = gr.Textbox(label="Transcription", interactive=False)
                audio_norm_out = gr.Textbox(label="Normalized Urdu", interactive=False)
                audio_analysis_out = gr.Markdown(label="Analysis")
                audio_conf_out = gr.Textbox(label="Speech Confidence", interactive=False)
                audio_btn.click(
                    transcribe_and_analyze,
                    inputs=[audio_input],
                    outputs=[
                        transcript_out,
                        audio_norm_out,
                        audio_analysis_out,
                        audio_conf_out,
                    ],
                )

            with gr.Tab("Named Entities"):
                ner_input = gr.Textbox(
                    label="Input text",
                    placeholder="Imran Khan ne Lahore mein PTI ki rally ki...",
                    lines=3,
                )
                ner_btn = gr.Button("Find Entities", variant="primary")
                ner_out = gr.Markdown(label="Entities")
                ner_btn.click(find_entities, inputs=[ner_input], outputs=[ner_out])

            with gr.Tab("Simplify"):
                simp_input = gr.Textbox(
                    label="Urdu text to simplify",
                    placeholder="حکومت نے ضروری تعلیم کے لیے نئی معلومات جاری کی...",
                    lines=3,
                )
                simp_btn = gr.Button("Simplify", variant="primary")
                simp_out = gr.Textbox(label="Simplified text", interactive=False)
                simp_changes = gr.Markdown(label="Changes")
                simp_btn.click(
                    simplify_text, inputs=[simp_input], outputs=[simp_out, simp_changes]
                )

        gr.Examples(
            examples=[
                ["yar mujhe pareshan mat karo bro"],
                ["job available, 50000 per week, send processing fee"],
                ["aaj weather bohat achha hai"],
                ["bhai ye to scam lag raha hai, paise mat bhejo"],
                ["free iphone jeetny k liye link click karein"],
            ],
            inputs=[text_input],
        )

    demo.launch(server_name="0.0.0.0", server_port=7860)


if __name__ == "__main__":
    main()
