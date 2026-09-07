import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.endpoints import router

app = FastAPI(
    title="UrduStack",
    description="A unified, code-switch-aware Urdu NLP infrastructure layer.",
    version="0.1.0",
)

# Allows a separately-hosted frontend (or the WhatsApp bot's local dev server)
# to call this API from a browser. Defaults to "*" for demo/hackathon use;
# set CORS_ALLOW_ORIGINS to a comma-separated list of real origins in
# production, since "*" combined with credentials is unsafe for anything
# beyond a public, read-mostly demo API like this one.
_allow_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_origins == "*" else _allow_origins.split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router)

static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def root():
        return FileResponse(static_dir / "index.html")
