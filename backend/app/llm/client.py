"""Ollama (yerel LLM) istemcisi.

Ücretsiz ve tamamen yerel çalışması için Anthropic yerine Ollama kullanılır;
sözleşme metinleri hiçbir zaman bilgisayardan dışarı çıkmaz. API şekli
(complete / complete_json / stream_text) değişmediği için çağıran servisler
(risk.py, qa.py, ingest_service.py) bu değişiklikten etkilenmez.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Iterator

import ollama

from ..config import settings

logger = logging.getLogger(__name__)

_client: ollama.Client | None = None


class LLMUnavailable(RuntimeError):
    """Ollama sunucusuna ulaşılamıyor ya da model kurulu değil."""


def get_client() -> ollama.Client:
    global _client
    if _client is not None:
        return _client
    _client = ollama.Client(host=settings.ollama_host)
    return _client


def _messages(system: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"role": "system", "content": system}, *messages]


def _friendly_error(exc: Exception) -> LLMUnavailable:
    message = str(exc)
    if "not found" in message.lower() or "404" in message:
        return LLMUnavailable(
            f"'{settings.ollama_model}' modeli kurulu değil. Terminalde "
            f"'ollama pull {settings.ollama_model}' çalıştırın."
        )
    return LLMUnavailable(
        f"Ollama'ya ulaşılamadı ({settings.ollama_host}). 'ollama serve' ile "
        "sunucunun çalıştığından emin olun."
    )


def complete(
    *,
    system: str,
    messages: list[dict[str, Any]],
    max_tokens: int = 4000,
    json_schema: dict[str, Any] | None = None,
) -> str:
    """Tek seferlik yanıt. `json_schema` verilirse çıktı şemaya zorlanır."""
    client = get_client()
    try:
        response = client.chat(
            model=settings.ollama_model,
            messages=_messages(system, messages),
            format=json_schema if json_schema is not None else None,
            options={"num_predict": max_tokens},
        )
    except (ollama.ResponseError, ConnectionError, OSError) as exc:
        raise _friendly_error(exc) from exc

    return (response.message.content or "").strip()


def complete_json(
    *,
    system: str,
    messages: list[dict[str, Any]],
    json_schema: dict[str, Any],
    max_tokens: int = 4000,
) -> dict[str, Any]:
    raw = complete(system=system, messages=messages, max_tokens=max_tokens, json_schema=json_schema)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Şema zorlaması olsa da savunmacı davranıp ilk JSON gövdesini kurtarmayı dene
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            return json.loads(raw[start : end + 1])
        raise


def stream_text(
    *,
    system: str,
    messages: list[dict[str, Any]],
    max_tokens: int = 2000,
) -> Iterator[str]:
    """Yanıtı parça parça üretir; sohbet arayüzünde anlık akış için kullanılır."""
    client = get_client()
    try:
        stream = client.chat(
            model=settings.ollama_model,
            messages=_messages(system, messages),
            options={"num_predict": max_tokens},
            stream=True,
        )
        for chunk in stream:
            if chunk.message and chunk.message.content:
                yield chunk.message.content
    except (ollama.ResponseError, ConnectionError, OSError) as exc:
        raise _friendly_error(exc) from exc
