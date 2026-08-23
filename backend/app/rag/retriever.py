"""Hibrit geri getirme (retrieval).

Üç bağımsız sinyal çalıştırılır ve sonuçlar **Reciprocal Rank Fusion** ile
birleştirilir:

1. **BM25** — Türkçe kök yaklaşımı üzerinde sözcüksel eşleşme. "cezai şart",
   "gecikme faizi" gibi terimlerin birebir geçtiği maddeleri yakalar.
2. **Karakter n-gram TF-IDF** — ek/çekim ve yazım varyantlarına dayanıklı;
   "fesihte" ↔ "feshin" gibi çiftleri BM25 kaçırdığında devreye girer.
3. **Yoğun vektör** (opsiyonel) — "sözleşmeyi erken bitirebilir miyim?" gibi
   hiçbir anahtar kelimeyi paylaşmayan sorularda anlamsal eşleşme sağlar.

RRF tercih edilmesinin sebebi, üç sinyalin skor ölçeklerinin
karşılaştırılamaz olması; sıra tabanlı birleştirme normalizasyon gerektirmez.
"""

from __future__ import annotations

import math
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..ingest.chunker import clause_label
from . import embedder
from .textutil import char_ngrams, tokenize

BM25_K1 = 1.5
BM25_B = 0.75
RRF_K = 60

WEIGHT_BM25 = 1.0
WEIGHT_NGRAM = 0.55
WEIGHT_DENSE = 1.0

# chunk_id -> (tokens, ngram_counter) — süreç içi önbellek
_TOKEN_CACHE: dict[str, tuple[list[str], Counter]] = {}


@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    doc_title: str
    ordinal: int
    article_no: str | None
    heading: str | None
    text: str
    page_start: int | None
    score: float
    signals: dict[str, float]

    @property
    def label(self) -> str:
        return clause_label(self.article_no, self.heading, self.ordinal)

    def to_citation(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "doc_title": self.doc_title,
            "label": self.label,
            "page": self.page_start,
            "excerpt": self.text[:400].strip(),
            "score": round(self.score, 4),
        }


def _cached_features(chunk_id: str, text: str) -> tuple[list[str], Counter]:
    cached = _TOKEN_CACHE.get(chunk_id)
    if cached is None:
        cached = (tokenize(text), Counter(char_ngrams(text)))
        if len(_TOKEN_CACHE) > 20000:  # sınırsız büyümeyi engelle
            _TOKEN_CACHE.clear()
        _TOKEN_CACHE[chunk_id] = cached
    return cached


def invalidate(chunk_ids: list[str] | None = None) -> None:
    if chunk_ids is None:
        _TOKEN_CACHE.clear()
        return
    for cid in chunk_ids:
        _TOKEN_CACHE.pop(cid, None)


def _fetch_candidates(conn: sqlite3.Connection, doc_ids: list[str] | None) -> list[sqlite3.Row]:
    sql = (
        "SELECT c.id, c.doc_id, c.ordinal, c.article_no, c.heading, c.text, "
        "       c.page_start, c.embedding, d.title AS doc_title "
        "FROM chunks c JOIN documents d ON d.id = c.doc_id"
    )
    params: list[Any] = []
    if doc_ids:
        placeholders = ",".join("?" for _ in doc_ids)
        sql += f" WHERE c.doc_id IN ({placeholders})"
        params = list(doc_ids)
    sql += " ORDER BY c.doc_id, c.ordinal"
    return conn.execute(sql, params).fetchall()


def _bm25_ranking(query_tokens: list[str], docs: list[tuple[str, list[str]]]) -> dict[str, float]:
    if not query_tokens or not docs:
        return {}
    n = len(docs)
    lengths = {cid: len(toks) for cid, toks in docs}
    avgdl = sum(lengths.values()) / n or 1.0

    freqs = {cid: Counter(toks) for cid, toks in docs}
    df: Counter = Counter()
    for counter in freqs.values():
        df.update(counter.keys())

    scores: dict[str, float] = defaultdict(float)
    for term in set(query_tokens):
        term_df = df.get(term, 0)
        if term_df == 0:
            continue
        idf = math.log(1 + (n - term_df + 0.5) / (term_df + 0.5))
        for cid, counter in freqs.items():
            tf = counter.get(term, 0)
            if not tf:
                continue
            denom = tf + BM25_K1 * (1 - BM25_B + BM25_B * lengths[cid] / avgdl)
            scores[cid] += idf * tf * (BM25_K1 + 1) / denom
    return dict(scores)


def _ngram_ranking(query: str, docs: list[tuple[str, Counter]]) -> dict[str, float]:
    query_counts = Counter(char_ngrams(query))
    if not query_counts or not docs:
        return {}
    n = len(docs)
    df: Counter = Counter()
    for _, counts in docs:
        df.update(counts.keys())

    def weight(counts: Counter) -> dict[str, float]:
        return {
            gram: (1 + math.log(freq)) * math.log(1 + n / (df.get(gram, 0) + 1))
            for gram, freq in counts.items()
        }

    qvec = weight(query_counts)
    qnorm = math.sqrt(sum(v * v for v in qvec.values())) or 1.0

    scores: dict[str, float] = {}
    for cid, counts in docs:
        dvec = weight(counts)
        dnorm = math.sqrt(sum(v * v for v in dvec.values())) or 1.0
        shared = qvec.keys() & dvec.keys()
        if not shared:
            continue
        dot = sum(qvec[g] * dvec[g] for g in shared)
        scores[cid] = dot / (qnorm * dnorm)
    return scores


def _dense_ranking(query: str, rows: list[sqlite3.Row]) -> dict[str, float]:
    vectors, ids = [], []
    for row in rows:
        vec = embedder.from_blob(row["embedding"])
        if vec is not None and vec.size:
            vectors.append(vec)
            ids.append(row["id"])
    if not vectors:
        return {}
    query_vec = embedder.encode([query])
    if query_vec is None:
        return {}
    matrix = np.vstack(vectors)
    sims = matrix @ query_vec[0]
    return {cid: float(score) for cid, score in zip(ids, sims)}


def _rrf(rankings: list[tuple[dict[str, float], float]]) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    fused: dict[str, float] = defaultdict(float)
    signals: dict[str, dict[str, float]] = defaultdict(dict)
    names = ["bm25", "ngram", "dense"]
    for (scores, weight), name in zip(rankings, names):
        ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        for rank, (cid, raw) in enumerate(ordered, start=1):
            fused[cid] += weight / (RRF_K + rank)
            signals[cid][name] = round(raw, 4)
    return dict(fused), dict(signals)


def retrieve(
    conn: sqlite3.Connection,
    query: str,
    *,
    doc_ids: list[str] | None = None,
    top_k: int = 8,
    per_doc_cap: int | None = None,
) -> list[RetrievedChunk]:
    """Sorguya en uygun maddeleri döndürür.

    `per_doc_cap`, çok belgeli karşılaştırmada tek bir sözleşmenin sonuç
    listesini domine etmesini engeller.
    """
    rows = _fetch_candidates(conn, doc_ids)
    if not rows:
        return []

    features = {row["id"]: _cached_features(row["id"], row["text"]) for row in rows}
    token_docs = [(cid, feats[0]) for cid, feats in features.items()]
    ngram_docs = [(cid, feats[1]) for cid, feats in features.items()]

    rankings = [
        (_bm25_ranking(tokenize(query), token_docs), WEIGHT_BM25),
        (_ngram_ranking(query, ngram_docs), WEIGHT_NGRAM),
        (_dense_ranking(query, rows) if embedder.is_available() else {}, WEIGHT_DENSE),
    ]
    fused, signals = _rrf(rankings)
    if not fused:
        return []

    by_id = {row["id"]: row for row in rows}
    ordered = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)

    results: list[RetrievedChunk] = []
    per_doc: Counter = Counter()
    for cid, score in ordered:
        row = by_id[cid]
        if per_doc_cap and per_doc[row["doc_id"]] >= per_doc_cap:
            continue
        per_doc[row["doc_id"]] += 1
        results.append(
            RetrievedChunk(
                chunk_id=cid,
                doc_id=row["doc_id"],
                doc_title=row["doc_title"],
                ordinal=row["ordinal"],
                article_no=row["article_no"],
                heading=row["heading"],
                text=row["text"],
                page_start=row["page_start"],
                score=score,
                signals=signals.get(cid, {}),
            )
        )
        if len(results) >= top_k:
            break
    return results
