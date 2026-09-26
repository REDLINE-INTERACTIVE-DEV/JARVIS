"""SQLite-backed persistent memory for JARVIS."""
import os
import sqlite3
from pathlib import Path
from threading import Lock

class MemoryStore:
    def __init__(self, path: str | None = None):
        configured = path or os.getenv("JARVIS_DB_PATH") or "data/jarvis.db"
        self.path = Path(configured)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        with self._db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
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
