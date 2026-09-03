from fastapi import FastAPI
from app.api.endpoints import router

app = FastAPI(
    title="UrduStack",
    description="A unified, code-switch-aware Urdu NLP infrastructure layer.",
    version="0.1.0",
)

app.include_router(router)
