"""SQLite tabanlı kalıcı depolama katmanı.

Harici bir ORM kullanılmaz; şema küçük ve sorgular okunabilir olacak şekilde
doğrudan sqlite3 üzerinden yürütülür. Vektörler float32 BLOB olarak saklanır.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Iterator

from .config import settings

DB_PATH = settings.data_dir / "app.db"
_lock = threading.Lock()

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS documents (
    id            TEXT PRIMARY KEY,
    filename      TEXT NOT NULL,
    title         TEXT NOT NULL,
    doc_type      TEXT,
    parties       TEXT,            -- JSON list
    effective_date TEXT,
    governing_law TEXT,
    page_count    INTEGER DEFAULT 0,
    char_count    INTEGER DEFAULT 0,
    clause_count  INTEGER DEFAULT 0,
    status        TEXT DEFAULT 'hazir',
    risk_score    REAL,
    created_at    TEXT NOT NULL,
    raw_text      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    id         TEXT PRIMARY KEY,
    doc_id     TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    ordinal    INTEGER NOT NULL,
    article_no TEXT,
    heading    TEXT,
    text       TEXT NOT NULL,
    page_start INTEGER,
    page_end   INTEGER,
    embedding  BLOB
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);

CREATE TABLE IF NOT EXISTS risks (
    id             TEXT PRIMARY KEY,
    doc_id         TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    rule_id        TEXT,
    category       TEXT NOT NULL,
    severity       TEXT NOT NULL,        -- kritik | yuksek | orta | dusuk | bilgi
    score          REAL DEFAULT 0,
    title          TEXT NOT NULL,
    clause_ref     TEXT,
    chunk_id       TEXT,
    excerpt        TEXT,
    rationale      TEXT,
    recommendation TEXT,
    options        TEXT,                 -- JSON list[{label, detail, impact}]
    source         TEXT DEFAULT 'kural', -- kural | llm
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_risks_doc ON risks(doc_id);

CREATE TABLE IF NOT EXISTS analyses (
    doc_id     TEXT PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
    payload    TEXT NOT NULL,            -- JSON
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id         TEXT PRIMARY KEY,
    thread_id  TEXT NOT NULL,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    citations  TEXT,                     -- JSON
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    """Her istek için kısa ömürlü bağlantı; yazmalar süreç içi kilitle serileştirilir."""
    conn = _connect()
    try:
        with _lock:
            yield conn
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    conn = _connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row | None, json_fields: tuple[str, ...] = ()) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    for field in json_fields:
        value = data.get(field)
        data[field] = json.loads(value) if value else None
    return data
