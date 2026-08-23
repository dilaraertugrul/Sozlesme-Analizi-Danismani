"""Belge yükleme, listeleme, görüntüleme ve silme uç noktaları."""

from __future__ import annotations

import json

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..db import get_db
from ..ingest.chunker import clause_label
from ..services import ingest_service

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("")
async def upload_documents(files: list[UploadFile] = File(...)):
    """Bir veya birden fazla sözleşmeyi yükler ve indeksler."""
    if not files:
        raise HTTPException(status_code=400, detail="Dosya seçilmedi.")

    uploaded, failed = [], []
    for upload in files:
        try:
            content = await upload.read()
            path = ingest_service.save_upload(upload.filename or "belge", content)
        except ValueError as exc:
            failed.append({"filename": upload.filename, "error": str(exc)})
            continue

        try:
            with get_db() as conn:
                uploaded.append(ingest_service.ingest(conn, path, upload.filename or path.name))
        except Exception as exc:
            path.unlink(missing_ok=True)
            failed.append({"filename": upload.filename, "error": str(exc)})

    if not uploaded and failed:
        raise HTTPException(status_code=400, detail=failed[0]["error"])

    return {"uploaded": uploaded, "failed": failed}


@router.get("")
def list_documents():
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, filename, title, doc_type, parties, page_count, char_count,
                      clause_count, risk_score, created_at,
                      (SELECT COUNT(*) FROM risks r WHERE r.doc_id = d.id) AS risk_count
               FROM documents d ORDER BY created_at DESC"""
        ).fetchall()

    return [
        {
            **dict(row),
            "parties": json.loads(row["parties"]) if row["parties"] else [],
            "analyzed": row["risk_count"] > 0,
        }
        for row in rows
    ]


@router.get("/{doc_id}")
def get_document(doc_id: str):
    with get_db() as conn:
        row = conn.execute(
            """SELECT id, filename, title, doc_type, parties, effective_date, governing_law,
                      page_count, char_count, clause_count, risk_score, created_at
               FROM documents WHERE id = ?""",
            (doc_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Sözleşme bulunamadı.")

        analysis = conn.execute(
            "SELECT payload FROM analyses WHERE doc_id = ?", (doc_id,)
        ).fetchone()
        chunks = conn.execute(
            "SELECT id, ordinal, article_no, heading, text, page_start "
            "FROM chunks WHERE doc_id = ? ORDER BY ordinal",
            (doc_id,),
        ).fetchall()

    payload = json.loads(analysis["payload"]) if analysis else {}
    metadata = payload.get("metadata", {})

    return {
        **dict(row),
        "parties": json.loads(row["parties"]) if row["parties"] else [],
        "summary": metadata.get("summary", ""),
        "key_obligations": metadata.get("key_obligations", []),
        "value": metadata.get("value"),
        "end_date": metadata.get("end_date"),
        "clauses": [
            {
                "id": c["id"],
                "ordinal": c["ordinal"],
                "article_no": c["article_no"],
                "heading": c["heading"],
                "label": clause_label(c["article_no"], c["heading"], c["ordinal"]),
                "text": c["text"],
                "page": c["page_start"],
            }
            for c in chunks
        ],
    }


@router.delete("/{doc_id}")
def delete_document(doc_id: str):
    with get_db() as conn:
        exists = conn.execute("SELECT 1 FROM documents WHERE id = ?", (doc_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Sözleşme bulunamadı.")
        ingest_service.delete_document(conn, doc_id)
    return {"deleted": doc_id}
