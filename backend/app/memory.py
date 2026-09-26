import sqlite3
from pathlib import Path
from threading import Lock
class MemoryStore:
 def __init__(self,path="data/jarvis.db"):
  self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self.lock=Lock()
  with self._db() as db: db.execute("CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,content TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP)"); db.commit()
 def _db(self): return sqlite3.connect(self.path,check_same_thread=False)
 def add(self,kind,content):
  with self.lock,self._db() as db: cur=db.execute("INSERT INTO memories(kind,content) VALUES(?,?)",(kind,content)); db.commit(); return cur.lastrowid
 def recent(self,limit=20):
  with self.lock,self._db() as db: return [{"id":r[0],"kind":r[1],"content":r[2],"created_at":r[3]} for r in db.execute("SELECT id,kind,content,created_at FROM memories ORDER BY id DESC LIMIT ?",(limit,))]