"""
Hugging Face Spaces entrypoint.

Serves the FastAPI backend and mounts the unified Gradio playground at the root path.
Run locally with:
    python app.py
"""

import uvicorn

from app.main import app as fastapi_app
from playground import build_demo


if __name__ == "__main__":
    import gradio as gr

    demo = build_demo()
    app = gr.mount_gradio_app(fastapi_app, demo, path="/playground")
    uvicorn.run(app, host="0.0.0.0", port=7860)
