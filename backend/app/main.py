"""Uygulama giriş noktası: FastAPI örneğini oluşturur, router'ları bağlar."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import init_db
from .routers import analysis, chat, documents

app = FastAPI(title="Hukuki Sözleşme Analiz Asistanı", version="0.1.0")

_frontend_origins = {settings.frontend_origin}
if "localhost" in settings.frontend_origin:
    _frontend_origins.add(settings.frontend_origin.replace("localhost", "127.0.0.1"))
elif "127.0.0.1" in settings.frontend_origin:
    _frontend_origins.add(settings.frontend_origin.replace("127.0.0.1", "localhost"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(_frontend_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(analysis.router)
app.include_router(chat.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "llm_enabled": settings.llm_enabled}
