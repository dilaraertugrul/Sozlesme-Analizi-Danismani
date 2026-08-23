"""Türkçe metin normalizasyonu.

Türkçe sondan eklemeli bir dildir: "fesih", "feshin", "feshedilmesi", "fesihte"
sözlükte dört ayrı belirteçtir. Tam bir morfolojik çözümleyici olmadan da,
hafif bir sonek kırpma ile BM25 geri çağırımı belirgin biçimde artar.
Ayrıca I/İ dönüşümü Python'un varsayılan `lower()` metodunda yanlıştır
("IŞIK".lower() -> "ışık" değil "ışık" beklenirken "ışık" alınamaz).
"""

from __future__ import annotations

import re

_LOWER_MAP = str.maketrans({"I": "ı", "İ": "i", "Ş": "ş", "Ğ": "ğ", "Ü": "ü", "Ö": "ö", "Ç": "ç"})
_ASCII_MAP = str.maketrans({"ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c"})

TOKEN_RE = re.compile(r"[0-9a-zçğıöşü]+")

STOPWORDS = {
    "ve", "veya", "ile", "ancak", "fakat", "ama", "de", "da", "ki", "ise", "için",
    "gibi", "kadar", "göre", "sonra", "önce", "daha", "çok", "az", "her", "bir",
    "bu", "şu", "o", "bunlar", "şunlar", "onlar", "olan", "olarak", "olup", "olmak",
    "eden", "edilen", "üzere", "tarafından", "hakkında", "ilgili", "ayrıca", "böyle",
    "hem", "ne", "mi", "mı", "mu", "mü", "en", "tüm", "bütün", "diğer", "aynı",
    "işbu", "mezkur", "mezkûr", "nezdinde", "nezdinden", "halinde", "hâlinde",
}

# En uzun ekten en kısaya doğru denenir; ilk eşleşme kırpılır.
_SUFFIXES = (
    "lerinden", "larından", "lerinin", "larının", "lerine", "larına", "leriyle",
    "larıyla", "sinden", "sından", "lerden", "lardan", "mesinin", "masının",
    "mesine", "masına", "nunda", "nında", "lerde", "larda", "leri", "ları",
    "sini", "sını", "nden", "ndan", "mesi", "ması", "inin", "ının", "unun",
    "ünün", "deki", "daki", "ler", "lar", "den", "dan", "nin", "nın", "nun",
    "nün", "ten", "tan", "ile", "in", "ın", "un", "ün", "de", "da", "te",
    "ta", "ye", "ya", "yi", "yı", "yu", "yü", "e", "a", "i", "ı", "u", "ü",
)


def tr_lower(text: str) -> str:
    return text.translate(_LOWER_MAP).lower()


def deaccent(text: str) -> str:
    return text.translate(_ASCII_MAP)


def stem(word: str) -> str:
    """Kök yaklaşımı: kelime en az 5 harfliyse tek bir sonek kırpılır."""
    if len(word) < 5 or word.isdigit():
        return word
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def tokenize(text: str, *, remove_stopwords: bool = True, do_stem: bool = True) -> list[str]:
    tokens = TOKEN_RE.findall(tr_lower(text))
    if remove_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS]
    if do_stem:
        tokens = [stem(t) for t in tokens]
    return tokens


def char_ngrams(text: str, n: int = 4) -> list[str]:
    """Karakter n-gramları: ek/çekim farklarına ve yazım varyantlarına dayanıklıdır."""
    normalized = deaccent(tr_lower(text))
    normalized = re.sub(r"[^0-9a-z]+", " ", normalized)
    normalized = f" {normalized.strip()} "
    if len(normalized) <= n:
        return [normalized]
    return [normalized[i : i + n] for i in range(len(normalized) - n + 1)]
