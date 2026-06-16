import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import Config

class HistoryStore:
    def __init__(self, db_path: Optional[Path] = None, check_same_thread: bool = False):
        if db_path is None:
            config = Config()
            db_path = config.UPLOAD_DIR.parent / "chat_history.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=check_same_thread,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        self.conn.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chats(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.commit()

    def add(self, question: str, answer: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
        cursor = self.conn.execute(
            "INSERT INTO chats (question, answer, metadata) VALUES (?, ?, ?)",
            (question, answer, metadata_json),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(
            "SELECT id, question, answer, metadata, created_at FROM chats ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def search(self, term: str, limit: int = 50) -> List[Dict[str, Any]]:
        query = f"%{term}%"
        cursor = self.conn.execute(
            "SELECT id, question, answer, metadata, created_at FROM chats "
            "WHERE question LIKE ? OR answer LIKE ? ORDER BY created_at DESC LIMIT ?",
            (query, query, limit),
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def delete(self, record_id: int) -> bool:
        cursor = self.conn.execute("DELETE FROM chats WHERE id = ?", (record_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def clear(self) -> None:
        self.conn.execute("DELETE FROM chats")
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        metadata = {}
        if row["metadata"]:
            try:
                metadata = json.loads(row["metadata"])
            except json.JSONDecodeError:
                metadata = {}
        return {"id": row["id"], "question": row["question"], "answer": row["answer"], "metadata": metadata, "created_at": row["created_at"]}

    def __enter__(self) -> "HistoryStore":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


_history_store = None

def get_history_store() -> HistoryStore:
    global _history_store
    if _history_store is None:
        _history_store = HistoryStore()
    return _history_store