"""Sohbet (RAG soru-cevap) uç noktaları."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..db import get_db
from ..rag import retriever
from ..services import qa

router = APIRouter(prefix="/api/chat", tags=["chat"])


class HistoryItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=2)
    doc_ids: list[str] | None = None
    history: list[HistoryItem] = Field(default_factory=list)
    top_k: int = Field(default=8, ge=3, le=20)


@router.post("/stream")
def chat_stream(body: ChatRequest):
    """Sunucu-gönderimli olay akışı: önce kaynaklar, sonra yanıt parçaları."""

    def event_source():
        with get_db() as conn:
            for event in qa.answer_stream(
                conn,
                body.question,
                doc_ids=body.doc_ids,
                history=[item.model_dump() for item in body.history],
                top_k=body.top_k,
            ):
                yield qa.sse(event)

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class SearchRequest(BaseModel):
    query: str = Field(min_length=2)
    doc_ids: list[str] | None = None
    top_k: int = Field(default=10, ge=1, le=30)


@router.post("/search")
def search(body: SearchRequest):
    """Model kullanmadan salt geri getirme — hangi maddenin neden seçildiğini gösterir."""
    with get_db() as conn:
        results = retriever.retrieve(conn, body.query, doc_ids=body.doc_ids, top_k=body.top_k)
    return {
        "results": [
            {**chunk.to_citation(), "signals": chunk.signals, "text": chunk.text}
            for chunk in results
        ]
    }
