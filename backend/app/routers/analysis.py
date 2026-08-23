"""Risk analizi, önerilen sorular ve karşılaştırma uç noktaları."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..db import get_db
from ..services import compare as compare_service
from ..services import qa, risk

router = APIRouter(prefix="/api", tags=["analysis"])


class AnalyzeRequest(BaseModel):
    use_llm: bool = True
    perspective: str | None = Field(
        default=None,
        description="Analizin hangi tarafın gözünden yapılacağı, ör. 'Yüklenici'",
    )


class CompareRequest(BaseModel):
    doc_ids: list[str] = Field(min_length=2, max_length=5)
    topics: list[str] | None = None
    use_llm: bool = True


@router.post("/documents/{doc_id}/analyze")
def analyze_document(doc_id: str, body: AnalyzeRequest | None = None):
    body = body or AnalyzeRequest()
    with get_db() as conn:
        try:
            return risk.analyze(
                conn, doc_id, use_llm=body.use_llm, perspective=body.perspective
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))


@router.get("/documents/{doc_id}/analysis")
def get_analysis(doc_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT payload FROM analyses WHERE doc_id = ?", (doc_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Bu sözleşme için analiz bulunamadı.")
    payload = json.loads(row["payload"])
    if "findings" not in payload:
        raise HTTPException(
            status_code=404,
            detail="Risk analizi henüz çalıştırılmadı. 'Risk analizi yap' düğmesini kullanın.",
        )
    return payload


@router.get("/documents/{doc_id}/suggested-questions")
def suggested_questions(doc_id: str):
    with get_db() as conn:
        try:
            return {"questions": qa.suggest_questions(conn, doc_id)}
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))


@router.post("/compare")
def compare_documents(body: CompareRequest):
    with get_db() as conn:
        try:
            return compare_service.compare(
                conn, body.doc_ids, topic_keys=body.topics, use_llm=body.use_llm
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))


@router.get("/compare/topics")
def compare_topics():
    return {
        "topics": [
            {"key": key, "label": label} for key, label, _ in compare_service.DEFAULT_TOPICS
        ]
    }
