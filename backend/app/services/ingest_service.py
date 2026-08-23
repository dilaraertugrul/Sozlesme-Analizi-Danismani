"""Belge alım hattı: dosya → metin → maddeler → vektörler → künye."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..config import settings
from ..ingest import extract as extractor
from ..ingest.chunker import chunk_document
from ..llm import client as llm
from ..llm import prompts
from ..rag import embedder, retriever

logger = logging.getLogger(__name__)


def save_upload(filename: str, content: bytes) -> Path:
    suffix = Path(filename).suffix.lower()
    if suffix not in settings.allowed_suffixes:
        raise ValueError(
            f"Desteklenmeyen dosya türü '{suffix}'. "
            f"Kabul edilenler: {', '.join(settings.allowed_suffixes)}"
        )
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise ValueError(f"Dosya boyutu {settings.max_upload_mb} MB sınırını aşıyor.")

    doc_id = uuid.uuid4().hex
    target = settings.data_dir / "uploads" / f"{doc_id}{suffix}"
    target.write_bytes(content)
    return target


def _extract_metadata(text: str) -> dict:
    """Künye çıkarımı. Model yoksa metinden basit sezgilerle doldurulur."""
    excerpt = text[:12000]
    try:
        return llm.complete_json(
            system=prompts.SUMMARY_SYSTEM,
            messages=[{"role": "user", "content": f"SÖZLEŞME METNİ:\n\n{excerpt}"}],
            json_schema=prompts.SUMMARY_SCHEMA,
            max_tokens=4000,
        )
    except Exception as exc:
        logger.info("Künye çıkarımı model olmadan yapılıyor (%s).", exc)
        first_line = next(
            (line.strip() for line in text.split("\n") if len(line.strip()) > 8), "Sözleşme"
        )
        return {
            "title": first_line[:120],
            "doc_type": None,
            "parties": [],
            "summary": "",
            "key_obligations": [],
        }


def ingest(conn: sqlite3.Connection, path: Path, original_name: str) -> dict:
    document = extractor.extract(path)
    chunks = chunk_document(document.text)

    metadata = _extract_metadata(document.text)
    doc_id = path.stem
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """INSERT INTO documents (id, filename, title, doc_type, parties, effective_date,
                                  governing_law, page_count, char_count, clause_count,
                                  status, created_at, raw_text)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            doc_id,
            original_name,
            metadata.get("title") or Path(original_name).stem,
            metadata.get("doc_type"),
            json.dumps(metadata.get("parties") or [], ensure_ascii=False),
            metadata.get("effective_date"),
            metadata.get("governing_law"),
            document.page_count,
            len(document.text),
            len(chunks),
            "hazir",
            now,
            document.text,
        ),
    )

    # Yoğun vektörler (sentence-transformers kuruluysa)
    vectors = embedder.encode([c.text for c in chunks]) if embedder.is_available() else None

    for index, chunk in enumerate(chunks):
        page = document.page_of(chunk.char_start)
        conn.execute(
            """INSERT INTO chunks (id, doc_id, ordinal, article_no, heading, text,
                                   page_start, page_end, embedding)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                f"{doc_id}-{index:04d}",
                doc_id,
                chunk.ordinal,
                chunk.article_no,
                chunk.heading,
                chunk.text,
                page,
                page,
                embedder.to_blob(vectors[index]) if vectors is not None else None,
            ),
        )

    retriever.invalidate()

    analysis_payload = {
        "summary": metadata.get("summary", ""),
        "key_obligations": metadata.get("key_obligations", []),
        "value": metadata.get("value"),
        "end_date": metadata.get("end_date"),
    }
    conn.execute(
        "INSERT INTO analyses (doc_id, payload, created_at) VALUES (?,?,?) "
        "ON CONFLICT(doc_id) DO UPDATE SET payload=excluded.payload",
        (doc_id, json.dumps({"metadata": analysis_payload}, ensure_ascii=False), now),
    )

    return {
        "id": doc_id,
        "title": metadata.get("title") or Path(original_name).stem,
        "doc_type": metadata.get("doc_type"),
        "clause_count": len(chunks),
        "page_count": document.page_count,
        "char_count": len(document.text),
        "summary": metadata.get("summary", ""),
        "key_obligations": metadata.get("key_obligations", []),
        "parties": metadata.get("parties", []),
        "created_at": now,
    }


def delete_document(conn: sqlite3.Connection, doc_id: str) -> None:
    chunk_ids = [
        row["id"] for row in conn.execute("SELECT id FROM chunks WHERE doc_id = ?", (doc_id,))
    ]
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    retriever.invalidate(chunk_ids)
    for suffix in settings.allowed_suffixes:
        candidate = settings.data_dir / "uploads" / f"{doc_id}{suffix}"
        if candidate.exists():
            candidate.unlink()
