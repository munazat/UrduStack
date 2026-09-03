from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.endpoints import router

app = FastAPI(
    title="UrduStack",
    description="A unified, code-switch-aware Urdu NLP infrastructure layer.",
    version="0.1.0",
)

app.include_router(router)

static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def root():
        return FileResponse(static_dir / "index.html")
