"""Madde farkındalıklı parçalama (clause-aware chunking).

Sözleşmelerde anlam birimi paragraf değil **maddedir**. Sabit uzunlukta kesmek,
"Madde 12 - Fesih" başlığını gövdesinden ayırıp atıfları anlamsız hale getirir.
Bu modül önce Türkçe hukuki metinlerdeki madde/başlık sınırlarını yakalar,
yalnızca bir madde tek başına çok uzunsa üst üste binmeli (overlap) alt
parçalara böler.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MAX_CHARS = 1800
OVERLAP_CHARS = 220
MIN_CHARS = 120

# "MADDE 12 -", "Madde 12.3", "Md. 4/A"
ARTICLE_RE = re.compile(
    r"^\s*(?:madde|madde\s*no|md\.?)\s*[:.]?\s*"
    r"(\d+(?:[./-]\w+)*)\s*[-–—.:)]?\s*(.{0,120})$",
    re.IGNORECASE,
)
# "12.", "12.1", "3.2.1)" gibi numaralı fıkra başlıkları
NUMBERED_RE = re.compile(r"^\s*(\d+(?:\.\d+){0,3})\s*[.)]\s+(\S.{0,120})$")
# "BÖLÜM II - GİZLİLİK", "EK-1", "KISIM 3"
SECTION_RE = re.compile(
    r"^\s*((?:bölüm|kısım|fasıl|ek)\s*[-–—]?\s*[\dIVXA-Z]+)\s*[-–—.:)]?\s*(.{0,120})$",
    re.IGNORECASE,
)

_TR_UPPER = "ABCDEFGHIJKLMNOPRSTUVYZÇĞİÖŞÜ"


@dataclass
class Chunk:
    ordinal: int
    text: str
    char_start: int
    article_no: str | None = None
    heading: str | None = None


def _is_caps_heading(line: str) -> bool:
    """Tamamı büyük harfli, kısa ve nokta ile bitmeyen satırlar başlık sayılır."""
    stripped = line.strip()
    if not (3 < len(stripped) <= 90) or stripped.endswith((".", ",", ";", ":")):
        return False
    letters = [c for c in stripped if c.isalpha()]
    if len(letters) < 3:
        return False
    upper = sum(1 for c in letters if c in _TR_UPPER)
    return upper / len(letters) >= 0.85


def _classify(line: str) -> tuple[str | None, str | None] | None:
    """Satır bir sınır ise (madde_no, başlık) döner, değilse None."""
    if match := ARTICLE_RE.match(line):
        return match.group(1), (match.group(2) or "").strip() or None
    if match := SECTION_RE.match(line):
        return match.group(1).strip(), (match.group(2) or "").strip() or None
    if match := NUMBERED_RE.match(line):
        number, rest = match.group(1), match.group(2).strip()
        # "1. Taraflar" bir başlıktır; "1. maddede belirtildiği üzere ..." değildir.
        if len(rest) <= 80 and not rest.endswith((".", ",", ";")):
            return number, rest
        if "." in number:  # 3.2 gibi alt fıkralar her hâlükârda sınırdır
            return number, None
        return None
    if _is_caps_heading(line):
        return None, line.strip()
    return None


def _split_long(text: str, base_start: int) -> list[tuple[str, int]]:
    """Uzun bir maddeyi cümle sınırlarına saygılı, örtüşmeli parçalara böler."""
    if len(text) <= MAX_CHARS:
        return [(text, base_start)]

    pieces: list[tuple[str, int]] = []
    cursor = 0
    while cursor < len(text):
        end = min(cursor + MAX_CHARS, len(text))
        if end < len(text):
            window = text[cursor:end]
            # Geriye doğru en yakın cümle sonunu ara
            for marker in (". ", ".\n", "; ", "\n\n"):
                idx = window.rfind(marker)
                if idx > MAX_CHARS * 0.5:
                    end = cursor + idx + len(marker)
                    break
        pieces.append((text[cursor:end].strip(), base_start + cursor))
        if end >= len(text):
            break
        cursor = max(end - OVERLAP_CHARS, cursor + 1)
    return [(t, s) for t, s in pieces if t]


def chunk_document(text: str) -> list[Chunk]:
    lines = text.split("\n")

    # 1) Satırları madde sınırlarına göre bloklara topla
    blocks: list[dict] = []
    current: dict | None = None
    offset = 0
    for line in lines:
        line_start = offset
        offset += len(line) + 1

        boundary = _classify(line)
        if boundary is not None:
            article_no, heading = boundary
            if current and current["lines"]:
                blocks.append(current)
            current = {
                "article_no": article_no,
                "heading": heading,
                "lines": [line],
                "start": line_start,
            }
            continue

        if current is None:
            current = {"article_no": None, "heading": None, "lines": [], "start": line_start}
        current["lines"].append(line)

    if current and any(l.strip() for l in current["lines"]):
        blocks.append(current)

    # 2) Çok kısa blokları bir öncekiyle birleştir (yalnız başlık satırları vb.)
    merged: list[dict] = []
    for block in blocks:
        body = "\n".join(block["lines"]).strip()
        if not body:
            continue
        if merged and len(body) < MIN_CHARS and merged[-1]["article_no"] is None:
            merged[-1]["lines"].extend(block["lines"])
            continue
        block["lines"] = body.split("\n")
        merged.append(block)

    # 3) Uzun blokları böl ve Chunk listesine dönüştür
    chunks: list[Chunk] = []
    for block in merged:
        body = "\n".join(block["lines"]).strip()
        for part, start in _split_long(body, block["start"]):
            chunks.append(
                Chunk(
                    ordinal=len(chunks),
                    text=part,
                    char_start=start,
                    article_no=block["article_no"],
                    heading=block["heading"],
                )
            )

    if not chunks and text.strip():
        chunks = [Chunk(ordinal=0, text=text.strip(), char_start=0)]
    return chunks


def clause_label(article_no: str | None, heading: str | None, ordinal: int) -> str:
    """Arayüzde ve atıflarda gösterilecek insan-okur etiket."""
    if article_no and heading:
        return f"Madde {article_no} — {heading}"
    if article_no:
        return f"Madde {article_no}"
    if heading:
        return heading
    return f"Bölüm {ordinal + 1}"
