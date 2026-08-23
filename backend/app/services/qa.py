"""RAG tabanlı soru-cevap ve soru önerisi."""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any, Iterator

from ..llm import client as llm
from ..llm import prompts
from ..rag import retriever
from ..rag.retriever import RetrievedChunk

logger = logging.getLogger(__name__)

MAX_HISTORY_TURNS = 8


def build_context(results: list[RetrievedChunk], *, multi_doc: bool) -> str:
    """Getirilen maddeleri [K1], [K2] etiketleriyle modele sunulacak biçime çevirir."""
    blocks = []
    for index, chunk in enumerate(results, start=1):
        header = f"[K{index}] {chunk.label}"
        if multi_doc:
            header += f"  ·  Sözleşme: {chunk.doc_title}"
        if chunk.page_start:
            header += f"  ·  Sayfa {chunk.page_start}"
        blocks.append(f"{header}\n{chunk.text}")
    return "\n\n---\n\n".join(blocks)


def _history_messages(history: list[dict[str, str]] | None) -> list[dict[str, Any]]:
    if not history:
        return []
    trimmed = history[-MAX_HISTORY_TURNS:]
    return [
        {"role": item["role"], "content": item["content"]}
        for item in trimmed
        if item.get("role") in ("user", "assistant") and item.get("content")
    ]


def answer_stream(
    conn: sqlite3.Connection,
    question: str,
    *,
    doc_ids: list[str] | None = None,
    history: list[dict[str, str]] | None = None,
    top_k: int = 8,
) -> Iterator[dict[str, Any]]:
    """Sunucu-gönderimli olay (SSE) akışı için sözlük üretir.

    Önce kaynaklar gönderilir; böylece arayüz yanıt yazılmaya başlamadan önce
    hangi maddelere bakıldığını gösterebilir.
    """
    multi_doc = not doc_ids or len(doc_ids) > 1
    results = retriever.retrieve(
        conn,
        question,
        doc_ids=doc_ids,
        top_k=top_k,
        per_doc_cap=4 if multi_doc else None,
    )

    if not results:
        yield {"type": "citations", "citations": []}
        yield {
            "type": "delta",
            "text": "Yüklü sözleşmelerde bu soruyla ilgili bir madde bulamadım. "
            "Soruyu farklı terimlerle ifade etmeyi ya da ilgili sözleşmeyi yüklemeyi deneyebilirsiniz.",
        }
        yield {"type": "done"}
        return

    yield {"type": "citations", "citations": [chunk.to_citation() for chunk in results]}

    context = build_context(results, multi_doc=multi_doc)
    user_message = (
        f"SÖZLEŞME ALINTILARI:\n\n{context}\n\n"
        f"---\n\nSORU: {question}"
    )

    messages = _history_messages(history) + [{"role": "user", "content": user_message}]

    try:
        for delta in llm.stream_text(system=prompts.QA_SYSTEM, messages=messages, max_tokens=8000):
            yield {"type": "delta", "text": delta}
    except llm.LLMUnavailable as exc:
        yield {"type": "error", "message": str(exc)}
        yield {
            "type": "delta",
            "text": "\n\n**Model katmanı devre dışı.** Aşağıda soruyla en ilgili maddeler listelenmiştir; "
            "yorum için Ollama'nın çalıştığından ve modelin kurulu olduğundan emin olun.",
        }
    except Exception as exc:
        logger.exception("Soru-cevap akışı başarısız oldu")
        yield {"type": "error", "message": f"Yanıt üretilemedi: {exc}"}

    yield {"type": "done"}


def suggest_questions(conn: sqlite3.Connection, doc_id: str) -> list[dict[str, str]]:
    """Sözleşmeye özgü önerilen sorular. Model yoksa risk kategorilerinden türetilir."""
    doc = conn.execute("SELECT title, doc_type FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if doc is None:
        raise ValueError("Belge bulunamadı.")

    headings = conn.execute(
        "SELECT article_no, heading FROM chunks WHERE doc_id = ? ORDER BY ordinal LIMIT 60",
        (doc_id,),
    ).fetchall()
    risks = conn.execute(
        "SELECT category, title FROM risks WHERE doc_id = ? ORDER BY score DESC LIMIT 12",
        (doc_id,),
    ).fetchall()

    try:
        outline = "\n".join(
            f"- {r['article_no'] or ''} {r['heading'] or ''}".strip()
            for r in headings
            if r["article_no"] or r["heading"]
        )
        risk_lines = "\n".join(f"- [{r['category']}] {r['title']}" for r in risks) or "- (analiz yapılmadı)"
        payload = llm.complete_json(
            system=prompts.SUGGEST_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Sözleşme: {doc['title']} ({doc['doc_type'] or 'tür belirsiz'})\n\n"
                        f"MADDE BAŞLIKLARI:\n{outline or '- (başlık çıkarılamadı)'}\n\n"
                        f"TESPİT EDİLEN RİSKLER:\n{risk_lines}\n\n"
                        "Bu sözleşme için 6 adet önerilen soru üret."
                    ),
                }
            ],
            json_schema=prompts.SUGGEST_SCHEMA,
            max_tokens=2000,
        )
        return payload.get("questions", [])[:8]
    except Exception as exc:
        logger.info("Soru önerisi model katmanı kullanılamadı (%s); yedek listeye düşülüyor.", exc)
        return _fallback_questions(risks)


_FALLBACK_BY_CATEGORY = {
    "fesih": "Bu sözleşmede fesih koşulları neler ve hangi tarafa ne kadar ihbar süresi tanınmış?",
    "sorumluluk": "Tarafların sorumluluğu için bir üst sınır belirlenmiş mi?",
    "cezai_sart": "Cezai şart hangi hallerde işler ve tutarı nasıl hesaplanır?",
    "odeme": "Ödeme vadesi, gecikme faizi ve fiyat artış mekanizması nasıl düzenlenmiş?",
    "gizlilik": "Gizlilik yükümlülüğü ne kadar süre devam ediyor ve istisnaları neler?",
    "fikri_mulkiyet": "Sözleşme kapsamında üretilen çıktıların fikri mülkiyeti kime ait?",
    "kvkk": "Kişisel verilerin işlenmesi ve aktarımı nasıl düzenlenmiş?",
    "rekabet": "Rekabet yasağı hangi süre, coğrafya ve faaliyet konusuyla sınırlı?",
    "uyusmazlik": "Uyuşmazlık halinde yetkili mahkeme veya tahkim merci hangisi?",
    "devir": "Sözleşme karşı tarafın onayı olmadan devredilebilir mi?",
    "yenileme": "Sözleşme süresi ne kadar ve otomatik yenileme öngörülmüş mü?",
}

_GENERIC_QUESTIONS = [
    ("Bu sözleşmede fesih koşulları neler?", "risk"),
    ("Tarafların temel yükümlülükleri nelerdir?", "yukumluluk"),
    ("Ödeme koşulları ve vadeler nasıl düzenlenmiş?", "mali"),
    ("Sözleşmenin süresi ve yenileme mekanizması nedir?", "sure"),
    ("Uyuşmazlık halinde hangi merci yetkili?", "uyusmazlik"),
]


def _fallback_questions(risks: list[sqlite3.Row]) -> list[dict[str, str]]:
    questions: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in risks:
        text = _FALLBACK_BY_CATEGORY.get(row["category"])
        if text and text not in seen:
            seen.add(text)
            questions.append({"question": text, "category": "risk"})
    for text, category in _GENERIC_QUESTIONS:
        if len(questions) >= 6:
            break
        if text not in seen:
            seen.add(text)
            questions.append({"question": text, "category": category})
    return questions[:6]


def sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
