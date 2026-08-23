"""Uygulama yapılandırması. Ortam değişkenlerinden okunur."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    # Ollama: yerel, ücretsiz LLM sunucusu — API anahtarı gerekmez.
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434").strip()
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b").strip()
    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    ).strip()
    data_dir: Path = Path(os.getenv("DATA_DIR", BASE_DIR / "data")).resolve()
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

    # Yükleme sınırları
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "25"))
    allowed_suffixes: tuple[str, ...] = (".pdf", ".docx", ".txt", ".md")

    @property
    def llm_enabled(self) -> bool:
        return bool(self.ollama_model)


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
(settings.data_dir / "uploads").mkdir(parents=True, exist_ok=True)
