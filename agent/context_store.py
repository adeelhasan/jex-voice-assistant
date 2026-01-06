"""
Context storage for conversation memory.
Stores arbitrary JSON data with TTL and thread-safe access for scheduled jobs.
"""

import sqlite3
import json
import time
import uuid
from typing import Optional, Dict, Any, List
from threading import Lock


class ContextStore:
    """
    SQLite-backed storage for conversation context with JSON flexibility.

    Default TTL: 1 hour (3600 seconds) - suitable for weather, emails, calendar.
    Weather data refreshes hourly to stay current.
    """

    def __init__(self, db_path: str = "context.db", ttl_seconds: int = 3600):
        self.db_path = db_path
        self.ttl_seconds = ttl_seconds  # Default: 1 hour
        self._lock = Lock()  # Thread-safe for scheduled jobs
        self._init_db()

    def _init_db(self):
        """Create tables if not exists."""
        with sqlite3.connect(self.db_path) as conn:
            # Existing context table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS context (
                    context_type TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL,
                    metadata_json TEXT,
                    updated_at REAL NOT NULL
                )
            """)

            # NEW: Tasks table for background task queue
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    params_json TEXT,
                    result_json TEXT,
                    error_message TEXT,
                    created_at REAL NOT NULL,
                    started_at REAL,
                    completed_at REAL,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3
                )
            """)

            # NEW: Announcements table for proactive notifications
            conn.execute("""
                CREATE TABLE IF NOT EXISTS announcements (
                    announcement_id TEXT PRIMARY KEY,
                    task_id TEXT,
                    message TEXT NOT NULL,
                    title TEXT,
                    priority INTEGER DEFAULT 1,
                    announced BOOLEAN DEFAULT FALSE,
                    announced_at REAL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id)
                )
            """)

            # Create indices for efficient querying
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_announcements_announced ON announcements(announced)")

            conn.commit()

    def save(self, context_type: str, data: Any, metadata: Optional[Dict] = None):
        """
        Store or update context data.

        Args:
            context_type: Label like 'emails', 'calendar', 'flights'
            data: Any JSON-serializable data
            metadata: Optional metadata (source query, filter params, etc.)
        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO context (context_type, data_json, metadata_json, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    context_type,
                    json.dumps(data),
                    json.dumps(metadata or {}),
                    time.time()
                ))
                conn.commit()

    def get(self, context_type: str) -> Optional[Any]:
        """Retrieve data by type, returns None if expired or not found."""
        result = self.get_with_metadata(context_type)
        return result['data'] if result else None

    def get_with_metadata(self, context_type: str) -> Optional[Dict]:
        """Get data + metadata, with expiration check."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute("""
                    SELECT data_json, metadata_json, updated_at
                    FROM context
                    WHERE context_type = ?
                """, (context_type,)).fetchone()

                if not row:
                    return None

                data_json, metadata_json, updated_at = row
                age = time.time() - updated_at

                # Check if expired
                if age > self.ttl_seconds:
                    self.clear(context_type)  # Auto-cleanup
                    return None

                return {
                    'data': json.loads(data_json),
                    'metadata': json.loads(metadata_json),
                    'age_seconds': age
                }

    def clear(self, context_type: Optional[str] = None):
        """Clear specific type or all context."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                if context_type:
                    conn.execute("DELETE FROM context WHERE context_type = ?", (context_type,))
                else:
                    conn.execute("DELETE FROM context")
                conn.commit()

    # ===== Task Management Methods =====

    def create_task(self, task_type: str, params: Optional[Dict] = None) -> str:
        """Create a new background task, return task_id"""
        task_id = str(uuid.uuid4())
        params_json = json.dumps(params) if params else None

        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO tasks (task_id, task_type, status, params_json, created_at) VALUES (?, ?, ?, ?, ?)",
                    (task_id, task_type, 'pending', params_json, time.time())
                )
                conn.commit()

        return task_id

    def update_task_status(self, task_id: str, status: str, result: Optional[Any] = None, error: Optional[str] = None):
        """Update task status and optionally store result"""
        result_json = json.dumps(result) if result else None
        now = time.time()

        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                if status == 'running':
                    conn.execute(
                        "UPDATE tasks SET status = ?, started_at = ? WHERE task_id = ?",
                        (status, now, task_id)
                    )
                elif status in ('completed', 'failed'):
                    conn.execute(
                        "UPDATE tasks SET status = ?, completed_at = ?, result_json = ?, error_message = ? WHERE task_id = ?",
                        (status, now, result_json, error, task_id)
                    )
                else:
                    conn.execute(
                        "UPDATE tasks SET status = ? WHERE task_id = ?",
                        (status, task_id)
                    )
                conn.commit()

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get task status and details"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT task_id, task_type, status, params_json, result_json, error_message, created_at, started_at, completed_at FROM tasks WHERE task_id = ?",
                    (task_id,)
                )
                row = cursor.fetchone()

        if not row:
            return None

        return {
            'task_id': row[0],
            'task_type': row[1],
            'status': row[2],
            'params': json.loads(row[3]) if row[3] else None,
            'result': json.loads(row[4]) if row[4] else None,
            'error': row[5],
            'created_at': row[6],
            'started_at': row[7],
            'completed_at': row[8]
        }

    def get_pending_tasks(self) -> List[Dict]:
        """Get all pending tasks ordered by creation time"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT task_id, task_type, params_json, created_at FROM tasks WHERE status = 'pending' ORDER BY created_at ASC"
                )
                rows = cursor.fetchall()

        return [
            {
                'task_id': row[0],
                'task_type': row[1],
                'params': json.loads(row[2]) if row[2] else None,
                'created_at': row[3]
            }
            for row in rows
        ]

    def create_announcement(self, task_id: str, message: str, title: Optional[str] = None) -> str:
        """Create announcement for completed task"""
        announcement_id = str(uuid.uuid4())

        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO announcements (announcement_id, task_id, message, title, created_at) VALUES (?, ?, ?, ?, ?)",
                    (announcement_id, task_id, message, title, time.time())
                )
                conn.commit()

        return announcement_id

    def get_pending_announcements(self) -> List[Dict]:
        """Get unannounced messages"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT announcement_id, task_id, message, title, created_at FROM announcements WHERE announced = FALSE ORDER BY created_at ASC"
                )
                rows = cursor.fetchall()

        return [
            {
                'announcement_id': row[0],
                'task_id': row[1],
                'message': row[2],
                'title': row[3],
                'created_at': row[4]
            }
            for row in rows
        ]

    def mark_announced(self, announcement_id: str):
        """Mark announcement as delivered"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE announcements SET announced = TRUE, announced_at = ? WHERE announcement_id = ?",
                    (time.time(), announcement_id)
                )
                conn.commit()


# Global singleton
_context_store = None


def get_context_store() -> ContextStore:
    global _context_store
    if _context_store is None:
        _context_store = ContextStore()
    return _context_store
