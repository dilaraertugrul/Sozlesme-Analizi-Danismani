"""Opsiyonel yoğun (dense) vektör gömme katmanı.

`sentence-transformers` kurulu değilse sistem sessizce devre dışı kalır ve
geri getirme yalnızca sözcüksel sinyallerle (BM25 + karakter n-gram) çalışır.
Bu, projenin ağır ML bağımlılıkları olmadan da ilk komutta ayağa kalkmasını sağlar.
"""

from __future__ import annotations

import logging
import threading

import numpy as np

from ..config import settings

logger = logging.getLogger(__name__)

_model = None
_load_attempted = False
_lock = threading.Lock()


def _load():
    global _model, _load_attempted
    with _lock:
        if _load_attempted:
            return _model
        _load_attempted = True
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            logger.info(
                "sentence-transformers kurulu değil — yoğun gömme devre dışı. "
                "Etkinleştirmek için: pip install -r requirements-embeddings.txt"
            )
            return None
        try:
            logger.info("Gömme modeli yükleniyor: %s", settings.embedding_model)
            _model = SentenceTransformer(settings.embedding_model)
            logger.info("Gömme modeli hazır.")
        except Exception as exc:  # indirme/uyumluluk hatalarında sistem çalışmaya devam eder
            logger.warning("Gömme modeli yüklenemedi (%s); yoğun arama devre dışı.", exc)
            _model = None
        return _model


def is_available() -> bool:
    return _load() is not None


def encode(texts: list[str]) -> np.ndarray | None:
    """Metinleri L2-normalize edilmiş float32 matrise dönüştürür (n, d)."""
    model = _load()
    if model is None or not texts:
        return None
    vectors = model.encode(
        texts, batch_size=16, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False
    )
    return np.asarray(vectors, dtype=np.float32)


def to_blob(vector: np.ndarray) -> bytes:
    return np.asarray(vector, dtype=np.float32).tobytes()


def from_blob(blob: bytes | None) -> np.ndarray | None:
    if not blob:
        return None
    return np.frombuffer(blob, dtype=np.float32)
