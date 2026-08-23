"""Risk analiz motoru: kural katmanı + LLM katmanı.

Kural katmanı deterministiktir ve API anahtarı olmadan da çalışır. LLM katmanı
üstüne bağlam yorumu, kaçırılan riskler ve müzakere seçenekleri ekler. İki
katmanın bulguları kategori bazında birleştirilir; aynı riskin iki kez
raporlanmasını önlemek için kural katmanı önceliklidir.
"""

from __future__ import annotations

import json
import logging
import math
import sqlite3
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..ingest.chunker import clause_label
from ..llm import client as llm
from ..llm import prompts
from ..rag.textutil import tr_lower
from .risk_rules import (
    CATEGORY_LABEL,
    COMPILED_RULES,
    SEVERITY_LABEL,
    SEVERITY_WEIGHT,
    applicable_absence_categories,
    classify_family,
)

logger = logging.getLogger(__name__)

MAX_CLAUSES_FOR_LLM = 60
MAX_CLAUSE_CHARS = 900


@dataclass
class Finding:
    category: str
    severity: str
    title: str
    rationale: str
    recommendation: str
    options: list[dict[str, str]] = field(default_factory=list)
    clause_ref: str | None = None
    chunk_id: str | None = None
    excerpt: str | None = None
    rule_id: str | None = None
    source: str = "kural"

    @property
    def score(self) -> float:
        return SEVERITY_WEIGHT.get(self.severity, 0.0)


# --------------------------------------------------------------------------- #
# Kural katmanı
# --------------------------------------------------------------------------- #


def run_rules(
    chunks: list[sqlite3.Row], *, applicable_categories: set[str] | None = None
) -> list[Finding]:
    """`applicable_categories`: None ise tüm kategoriler; aksi halde yokluk
    (absence) bulguları yalnızca bu kümedeki kategorilerde üretilir — bkz.
    `risk_rules.applicable_absence_categories`. Varlık (presence) bulguları
    her zaman üretilir; metinde fiilen geçen riskli bir ifade, sözleşme
    ailesinden bağımsız olarak raporlanmaya değerdir."""
    findings: list[Finding] = []
    seen_rules: set[str] = set()

    full_text_lower = tr_lower("\n".join(row["text"] for row in chunks))

    for row in chunks:
        lowered = tr_lower(row["text"])
        label = clause_label(row["article_no"], row["heading"], row["ordinal"])
        for rule in COMPILED_RULES:
            if rule.id in seen_rules:
                continue
            hit = rule.match(lowered)
            if not hit:
                continue
            seen_rules.add(rule.id)
            findings.append(
                Finding(
                    category=rule.category,
                    severity=rule.severity,
                    title=rule.title,
                    rationale=rule.rationale,
                    recommendation=rule.recommendation,
                    options=[asdict(o) for o in rule.options],
                    clause_ref=label,
                    chunk_id=row["id"],
                    excerpt=_excerpt_around(row["text"], hit),
                    rule_id=rule.id,
                    source="kural",
                )
            )

    # Yokluk riskleri: ilgili konu sözleşmenin hiçbir yerinde geçmiyorsa
    for rule in COMPILED_RULES:
        if not rule.absence_title or rule.id in seen_rules:
            continue
        if applicable_categories is not None and rule.category not in applicable_categories:
            continue
        if rule.is_present(full_text_lower):
            continue
        findings.append(
            Finding(
                category=rule.category,
                severity=rule.absence_severity or "orta",
                title=rule.absence_title,
                rationale=rule.absence_rationale or "",
                recommendation=rule.absence_recommendation or "",
                options=[asdict(o) for o in rule.options],
                clause_ref=None,
                chunk_id=None,
                excerpt=None,
                rule_id=f"{rule.id}::yokluk",
                source="kural",
            )
        )

    return findings


def _excerpt_around(text: str, hit: str, window: int = 240) -> str:
    """Eşleşmenin çevresinden okunabilir bir alıntı çıkarır."""
    lowered = tr_lower(text)
    index = lowered.find(tr_lower(hit)[:40])
    if index == -1:
        return text[:window].strip()
    start = max(0, index - window // 3)
    end = min(len(text), index + len(hit) + window)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{text[start:end].strip()}{suffix}"


# --------------------------------------------------------------------------- #
# LLM katmanı
# --------------------------------------------------------------------------- #


def _clause_digest(chunks: list[sqlite3.Row]) -> str:
    lines = []
    for row in chunks[:MAX_CLAUSES_FOR_LLM]:
        label = clause_label(row["article_no"], row["heading"], row["ordinal"])
        body = row["text"][:MAX_CLAUSE_CHARS].replace("\n", " ")
        lines.append(f"### {label}\n{body}")
    if len(chunks) > MAX_CLAUSES_FOR_LLM:
        lines.append(f"\n(… {len(chunks) - MAX_CLAUSES_FOR_LLM} madde daha; uzunluk nedeniyle kısaltıldı)")
    return "\n\n".join(lines)


def run_llm_layer(
    chunks: list[sqlite3.Row],
    rule_findings: list[Finding],
    *,
    perspective: str | None = None,
    family: str = "ticari",
    applicable_categories: set[str] | None = None,
) -> tuple[list[Finding], str, str]:
    """LLM bulgularını, genel değerlendirmeyi ve taraf dengesini döndürür."""
    already = "\n".join(f"- [{f.category}] {f.title}" for f in rule_findings) or "- (yok)"
    side = perspective or "sözleşmeyi yükleyen taraf"

    family_note = ""
    if applicable_categories is not None:
        allowed = ", ".join(sorted(applicable_categories)) or "(hiçbiri)"
        family_note = (
            f"\nBELGE TÜRÜ NOTU: Bu belge '{family}' ailesine ait. Ticari sözleşmelere özgü "
            "kategorilerde (gizlilik, fikri mülkiyet, rekabet yasağı, teminat, mücbir sebep, "
            "sigorta, denetim, cezai şart vb.) metinde fiilen böyle bir hüküm geçmiyorsa YALNIZCA "
            "'madde yok/eksik' diyerek yokluk bulgusu üretme — bu belge türünde zaten beklenmez. "
            f"Yokluk (eksiklik) türü bulguları yalnızca şu kategorilerle sınırlı tut: {allowed}. "
            "Metinde fiilen geçen riskli bir ifadeyi (varlık bulgusu, clause_ref ile) her zaman "
            "raporlayabilirsin."
        )

    user_content = (
        f"Analiz edilen taraf: {side}\n"
        f"{family_note}\n\n"
        f"KURAL MOTORUNUN TESPİT ETTİĞİ RİSKLER (bunları tekrar etme):\n{already}\n\n"
        f"SÖZLEŞME MADDELERİ:\n{_clause_digest(chunks)}"
    )

    payload = llm.complete_json(
        system=prompts.RISK_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
        json_schema=prompts.RISK_SCHEMA,
        max_tokens=16000,
    )

    findings = [
        Finding(
            category=item.get("category", "diger"),
            severity=item.get("severity", "orta"),
            title=item["title"],
            rationale=item.get("rationale", ""),
            recommendation=item.get("recommendation", ""),
            options=item.get("options", []),
            clause_ref=item.get("clause_ref"),
            excerpt=item.get("excerpt"),
            source="llm",
        )
        for item in payload.get("findings", [])
    ]

    if applicable_categories is not None:
        # Emniyet ağı: talimata uymayıp yine de ilgisiz kategoride yokluk
        # bulgusu üretirse (clause_ref'siz, yani metne dayanmayan bir iddia),
        # bu bulguyu ele — metne dayanan (clause_ref'li) bulgular her zaman kalır.
        findings = [
            f for f in findings if f.clause_ref or f.category in applicable_categories
        ]

    return findings, payload.get("overall_assessment", ""), payload.get("position", "dengeli")


# --------------------------------------------------------------------------- #
# Birleştirme, puanlama, kalıcılık
# --------------------------------------------------------------------------- #


def _dedupe(rule_findings: list[Finding], llm_findings: list[Finding]) -> list[Finding]:
    """Aynı kategoride benzer başlıklı LLM bulgularını eler (kural katmanı önceliklidir)."""
    def signature(text: str) -> set[str]:
        return {w for w in tr_lower(text).split() if len(w) > 4}

    kept = list(rule_findings)
    existing = [(f.category, signature(f.title)) for f in rule_findings]
    # Kural motoru zaten bu kategoride "madde yok/eksik" dediyse (clause_ref
    # yok), LLM'in aynı kategoride ürettiği başka bir clause_ref'siz "eksik"
    # anlatımı — başlığı ne kadar farklı ifade edilmiş olursa olsun — aynı
    # bulgunun tekrarıdır (bkz. "Fikri mülkiyet düzenlemesi yok" ⁄
    # "Fikri Mülkiyet Koruma Olmaması" gibi çiftler, kelime-örtüşme eşiğini
    # yakalayamıyordu).
    rule_absence_categories = {f.category for f in rule_findings if not f.chunk_id}

    for finding in llm_findings:
        if not finding.clause_ref and finding.category in rule_absence_categories:
            continue
        sig = signature(finding.title)
        duplicate = False
        for category, other in existing:
            if category != finding.category or not sig or not other:
                continue
            overlap = len(sig & other) / max(len(sig), 1)
            if overlap >= 0.55:
                duplicate = True
                break
        if not duplicate:
            kept.append(finding)
            existing.append((finding.category, sig))

    order = {"kritik": 0, "yuksek": 1, "orta": 2, "dusuk": 3, "bilgi": 4}
    kept.sort(key=lambda f: (order.get(f.severity, 5), f.category))
    return kept


def compute_score(findings: list[Finding]) -> float:
    """0–100 arası risk puanı. Doyum eğrisi kullanılır: tek bir kritik bulgu
    puanı hızla yükseltir, çok sayıda düşük bulgu ise 100'e dayanmaz."""
    raw = sum(f.score for f in findings)
    return round(100 * (1 - math.exp(-raw / 22)), 1)


def summarize_by_category(findings: list[Finding]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for finding in findings:
        bucket = buckets.setdefault(
            finding.category,
            {
                "category": finding.category,
                "label": CATEGORY_LABEL.get(finding.category, "Diğer"),
                "count": 0,
                "score": 0.0,
                "max_severity": "bilgi",
            },
        )
        bucket["count"] += 1
        bucket["score"] += finding.score
        if SEVERITY_WEIGHT.get(finding.severity, 0) > SEVERITY_WEIGHT.get(bucket["max_severity"], 0):
            bucket["max_severity"] = finding.severity

    for bucket in buckets.values():
        bucket["score"] = round(100 * (1 - math.exp(-bucket["score"] / 12)), 1)
    return sorted(buckets.values(), key=lambda b: b["score"], reverse=True)


def severity_counts(findings: list[Finding]) -> dict[str, int]:
    counts = {key: 0 for key in SEVERITY_LABEL}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    return counts


def analyze(
    conn: sqlite3.Connection,
    doc_id: str,
    *,
    use_llm: bool = True,
    perspective: str | None = None,
) -> dict[str, Any]:
    chunks = conn.execute(
        "SELECT id, ordinal, article_no, heading, text FROM chunks WHERE doc_id = ? ORDER BY ordinal",
        (doc_id,),
    ).fetchall()
    if not chunks:
        raise ValueError("Belge bulunamadı veya henüz işlenmedi.")

    doc_row = conn.execute("SELECT doc_type FROM documents WHERE id = ?", (doc_id,)).fetchone()
    doc_type = doc_row["doc_type"] if doc_row else None
    family = classify_family(doc_type)
    applicable_categories = applicable_absence_categories(doc_type)

    rule_findings = run_rules(chunks, applicable_categories=applicable_categories)

    llm_findings: list[Finding] = []
    assessment = ""
    position = "dengeli"
    llm_error: str | None = None

    if use_llm:
        try:
            llm_findings, assessment, position = run_llm_layer(
                chunks,
                rule_findings,
                perspective=perspective,
                family=family,
                applicable_categories=applicable_categories,
            )
        except llm.LLMUnavailable as exc:
            llm_error = str(exc)
        except Exception as exc:  # analiz kural katmanıyla tamamlanmaya devam eder
            logger.exception("LLM risk katmanı başarısız oldu")
            llm_error = f"Model katmanı çalıştırılamadı: {exc}"

    findings = _dedupe(rule_findings, llm_findings)
    score = compute_score(findings)

    if not assessment:
        counts = severity_counts(findings)
        assessment = (
            f"Kural motoru {len(findings)} bulgu tespit etti "
            f"({counts.get('kritik', 0)} kritik, {counts.get('yuksek', 0)} yüksek). "
            "Bağlamsal yorum için model katmanı devre dışı."
        )

    now = datetime.now(timezone.utc).isoformat()
    conn.execute("DELETE FROM risks WHERE doc_id = ?", (doc_id,))
    for finding in findings:
        conn.execute(
            """INSERT INTO risks (id, doc_id, rule_id, category, severity, score, title,
                                  clause_ref, chunk_id, excerpt, rationale, recommendation,
                                  options, source, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                uuid.uuid4().hex,
                doc_id,
                finding.rule_id,
                finding.category,
                finding.severity,
                finding.score,
                finding.title,
                finding.clause_ref,
                finding.chunk_id,
                finding.excerpt,
                finding.rationale,
                finding.recommendation,
                json.dumps(finding.options, ensure_ascii=False),
                finding.source,
                now,
            ),
        )

    # 'analyses' tablosundaki satır hem alım (ingest) künyesini hem risk analizini
    # taşır; mevcut 'metadata' anahtarını koruyarak üzerine yazıyoruz, aksi halde
    # risk analizi çalıştırıldığında özet/taraflar/yükümlülükler kaybolur.
    existing = conn.execute(
        "SELECT payload FROM analyses WHERE doc_id = ?", (doc_id,)
    ).fetchone()
    existing_metadata = json.loads(existing["payload"]).get("metadata") if existing else None

    payload = {
        "doc_id": doc_id,
        "risk_score": score,
        "contract_family": family,
        "position": position,
        "overall_assessment": assessment,
        "severity_counts": severity_counts(findings),
        "categories": summarize_by_category(findings),
        "findings": [
            {
                **asdict(finding),
                "severity_label": SEVERITY_LABEL.get(finding.severity, finding.severity),
                "category_label": CATEGORY_LABEL.get(finding.category, "Diğer"),
            }
            for finding in findings
        ],
        "llm_error": llm_error,
        "analyzed_at": now,
        "metadata": existing_metadata or {},
    }

    conn.execute(
        "INSERT INTO analyses (doc_id, payload, created_at) VALUES (?,?,?) "
        "ON CONFLICT(doc_id) DO UPDATE SET payload=excluded.payload, created_at=excluded.created_at",
        (doc_id, json.dumps(payload, ensure_ascii=False), now),
    )
    conn.execute("UPDATE documents SET risk_score = ? WHERE id = ?", (score, doc_id))
    return payload
