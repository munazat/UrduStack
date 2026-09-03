"""
Hugging Face Spaces entrypoint.

Serves the FastAPI backend and mounts the Gradio playground at the root path.
Run locally with:
    python app.py
"""

import gradio as gr
import uvicorn

from app.main import app as fastapi_app
from playground import analyze


def build_playground():
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
    return demo


if __name__ == "__main__":
    demo = build_playground()
    app = gr.mount_gradio_app(fastapi_app, demo, path="/")
    uvicorn.run(app, host="0.0.0.0", port=7860)
