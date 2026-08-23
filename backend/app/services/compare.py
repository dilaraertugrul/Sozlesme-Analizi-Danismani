"""Birden fazla sözleşmenin konu bazında karşılaştırılması.

Her konu için her sözleşmeden ayrı ayrı geri getirme yapılır (yoksa güçlü
sözleşme zayıfın maddelerini bastırır), ardından maddeler yan yana modele
sunulur. Model katmanı yoksa kural motorunun risk kategorileri üzerinden
deterministik bir matris üretilir.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

from ..llm import client as llm
from ..llm import prompts
from ..rag import retriever
from .risk_rules import CATEGORY_LABEL, SEVERITY_LABEL, SEVERITY_WEIGHT

logger = logging.getLogger(__name__)

DEFAULT_TOPICS: list[tuple[str, str, str]] = [
    ("fesih", "Fesih ve Sona Erme", "fesih hakkı ihbar süresi sözleşmenin sona ermesi haklı sebeple fesih"),
    ("sorumluluk", "Sorumluluk Sınırı", "sorumluluk sınırı tazminat üst sınırı dolaylı zarar sorumsuzluk"),
    ("odeme", "Ödeme Koşulları", "ödeme vadesi fatura bedel gecikme faizi fiyat artışı"),
    ("cezai_sart", "Cezai Şart", "cezai şart ceza gecikme cezası tazminat"),
    ("gizlilik", "Gizlilik", "gizlilik gizli bilgi ifşa etmeme sır saklama süresi"),
    ("fikri_mulkiyet", "Fikri Mülkiyet", "fikri mülkiyet telif hakkı mali haklar devir lisans"),
    ("kvkk", "Kişisel Veriler", "kişisel veri KVKK veri sorumlusu veri işleyen aktarım"),
    ("yenileme", "Süre ve Yenileme", "sözleşme süresi yürürlük otomatik yenileme uzama"),
    ("uyusmazlik", "Uyuşmazlık Çözümü", "yetkili mahkeme tahkim uygulanacak hukuk uyuşmazlık"),
    ("devir", "Devir ve Temlik", "devir temlik onay alt yüklenici üçüncü kişiye devir"),
]

CLAUSES_PER_DOC = 3
MAX_CLAUSE_CHARS = 700


def _collect_topic_clauses(
    conn: sqlite3.Connection, doc_ids: list[str], topics: list[tuple[str, str, str]]
) -> dict[str, dict[str, list[Any]]]:
    """topic_key -> doc_id -> ilgili maddeler"""
    collected: dict[str, dict[str, list[Any]]] = {}
    for key, _, query in topics:
        per_doc: dict[str, list[Any]] = {}
        for doc_id in doc_ids:
            per_doc[doc_id] = retriever.retrieve(
                conn, query, doc_ids=[doc_id], top_k=CLAUSES_PER_DOC
            )
        collected[key] = per_doc
    return collected


def _rule_matrix(conn: sqlite3.Connection, doc_ids: list[str]) -> list[dict[str, Any]]:
    """Kural motorunun bulgularından deterministik karşılaştırma matrisi."""
    rows = conn.execute(
        "SELECT doc_id, category, severity, title, clause_ref FROM risks "
        f"WHERE doc_id IN ({','.join('?' for _ in doc_ids)})",
        doc_ids,
    ).fetchall()

    grid: dict[str, dict[str, list[sqlite3.Row]]] = {}
    for row in rows:
        grid.setdefault(row["category"], {}).setdefault(row["doc_id"], []).append(row)

    matrix = []
    for category, per_doc in grid.items():
        cells = []
        for doc_id in doc_ids:
            findings = per_doc.get(doc_id, [])
            if not findings:
                cells.append(
                    {"doc_id": doc_id, "severity": None, "count": 0, "titles": [], "stance": "temiz"}
                )
                continue
            worst = max(findings, key=lambda f: SEVERITY_WEIGHT.get(f["severity"], 0))
            cells.append(
                {
                    "doc_id": doc_id,
                    "severity": worst["severity"],
                    "severity_label": SEVERITY_LABEL.get(worst["severity"], worst["severity"]),
                    "count": len(findings),
                    "titles": [f["title"] for f in findings[:3]],
                    "stance": "riskli",
                }
            )
        matrix.append(
            {
                "category": category,
                "label": CATEGORY_LABEL.get(category, "Diğer"),
                "cells": cells,
            }
        )

    matrix.sort(
        key=lambda entry: max(
            (SEVERITY_WEIGHT.get(c.get("severity") or "bilgi", 0) for c in entry["cells"]), default=0
        ),
        reverse=True,
    )
    return matrix


def _build_llm_input(
    docs: list[sqlite3.Row],
    topics: list[tuple[str, str, str]],
    collected: dict[str, dict[str, list[Any]]],
) -> str:
    lines = ["KARŞILAŞTIRILAN SÖZLEŞMELER:"]
    for doc in docs:
        lines.append(f"- {doc['id']}: {doc['title']} ({doc['doc_type'] or 'tür belirsiz'})")

    for key, label, _ in topics:
        lines.append(f"\n\n## KONU: {label}  (topic anahtarı: {key})")
        for doc in docs:
            chunks = collected[key].get(doc["id"], [])
            lines.append(f"\n### {doc['id']} — {doc['title']}")
            if not chunks:
                lines.append("(bu konuda ilgili madde bulunamadı)")
                continue
            for chunk in chunks:
                body = chunk.text[:MAX_CLAUSE_CHARS].replace("\n", " ")
                lines.append(f"- {chunk.label}: {body}")
    return "\n".join(lines)


def compare(
    conn: sqlite3.Connection,
    doc_ids: list[str],
    *,
    topic_keys: list[str] | None = None,
    use_llm: bool = True,
) -> dict[str, Any]:
    if len(doc_ids) < 2:
        raise ValueError("Karşılaştırma için en az iki sözleşme seçilmelidir.")
    if len(doc_ids) > 5:
        raise ValueError("Aynı anda en fazla beş sözleşme karşılaştırılabilir.")

    placeholders = ",".join("?" for _ in doc_ids)
    docs = conn.execute(
        f"SELECT id, title, doc_type, risk_score, parties FROM documents WHERE id IN ({placeholders})",
        doc_ids,
    ).fetchall()
    if len(docs) != len(doc_ids):
        raise ValueError("Seçilen sözleşmelerden biri bulunamadı.")

    # İstenen sıralamayı koru
    order = {doc_id: index for index, doc_id in enumerate(doc_ids)}
    docs = sorted(docs, key=lambda d: order[d["id"]])

    topics = DEFAULT_TOPICS
    if topic_keys:
        selected = {k for k in topic_keys}
        topics = [t for t in DEFAULT_TOPICS if t[0] in selected] or DEFAULT_TOPICS

    collected = _collect_topic_clauses(conn, doc_ids, topics)

    result: dict[str, Any] = {
        "documents": [
            {
                "id": doc["id"],
                "title": doc["title"],
                "doc_type": doc["doc_type"],
                "risk_score": doc["risk_score"],
                "parties": json.loads(doc["parties"]) if doc["parties"] else [],
            }
            for doc in docs
        ],
        "risk_matrix": _rule_matrix(conn, doc_ids),
        "clause_map": {
            key: {
                doc_id: [c.to_citation() for c in chunks]
                for doc_id, chunks in per_doc.items()
            }
            for key, per_doc in collected.items()
        },
        "topic_labels": {key: label for key, label, _ in topics},
        "headline": "",
        "topics": [],
        "llm_error": None,
    }

    if not use_llm:
        return result

    try:
        payload = llm.complete_json(
            system=prompts.COMPARE_SYSTEM,
            messages=[{"role": "user", "content": _build_llm_input(docs, topics, collected)}],
            json_schema=prompts.COMPARE_SCHEMA,
            max_tokens=16000,
        )
        result["headline"] = payload.get("headline", "")
        result["topics"] = payload.get("topics", [])
    except llm.LLMUnavailable as exc:
        result["llm_error"] = str(exc)
    except Exception as exc:
        logger.exception("Karşılaştırma model katmanı başarısız oldu")
        result["llm_error"] = f"Model katmanı çalıştırılamadı: {exc}"

    return result
