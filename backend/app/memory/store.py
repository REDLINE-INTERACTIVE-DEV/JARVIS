"""SQLite-backed persistent memory and cross-device event journal for JARVIS."""
import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

class MemoryStore:
    def __init__(self, path: str | None = None):
        configured = path or os.getenv("JARVIS_DB_PATH") or "data/jarvis.db"
        self.path = Path(configured)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        with self._db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            db.execute("""CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_key TEXT NOT NULL UNIQUE,
                source_device TEXT NOT NULL,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                reported_at TEXT
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_events_pending ON events(reported_at, created_at, id)")
            db.commit()

    def _db(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10, check_same_thread=False)
        db.row_factory = sqlite3.Row
        return db

    def add(self, kind: str, content: str) -> int:
        kind, content = kind.strip(), content.strip()
        if not kind or not content:
            raise ValueError("kind and content are required")
        with self._lock, self._db() as db:
            cursor = db.execute("INSERT INTO memories(kind, content) VALUES (?, ?)", (kind, content))
            db.commit()
            return int(cursor.lastrowid)

    def recent(self, limit: int = 20) -> list[dict]:
        limit = max(1, min(int(limit), 100))
        with self._lock, self._db() as db:
            rows = db.execute("SELECT id, kind, content, created_at FROM memories ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

    def add_event(self, source_device: str, event_type: str, title: str, content: str, external_id: str = "", created_at: str | None = None) -> dict:
        source_device, event_type, title, content = (x.strip() for x in (source_device, event_type, title, content))
        if not source_device or not event_type or not title or not content:
            raise ValueError("source_device, event_type, title and content are required")
        key_material = external_id.strip() or f"{source_device}|{event_type}|{title}|{content}"
        event_key = hashlib.sha256(key_material.encode("utf-8")).hexdigest()
        created_at = created_at or datetime.now(timezone.utc).isoformat()
        with self._lock, self._db() as db:
            db.execute("INSERT OR IGNORE INTO events(event_key,source_device,event_type,title,content,created_at) VALUES(?,?,?,?,?,?)",
                       (event_key, source_device, event_type, title, content, created_at))
            row = db.execute("SELECT * FROM events WHERE event_key = ?", (event_key,)).fetchone()
            db.commit()
        return dict(row)

    def pending_events(self, limit: int = 100) -> list[dict]:
        limit = max(1, min(int(limit), 500))
        with self._lock, self._db() as db:
            rows = db.execute("SELECT * FROM events WHERE reported_at IS NULL ORDER BY created_at ASC, id ASC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

    def mark_events_reported(self, event_ids: list[int]) -> int:
        ids = sorted({int(x) for x in event_ids})
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        with self._lock, self._db() as db:
            cur = db.execute(f"UPDATE events SET reported_at = ? WHERE id IN ({placeholders}) AND reported_at IS NULL",
                             (datetime.now(timezone.utc).isoformat(), *ids))
            db.commit()
            return int(cur.rowcount)
