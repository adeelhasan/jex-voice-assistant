"""
Context storage for conversation memory.
Stores arbitrary JSON data with TTL and thread-safe access for scheduled jobs.
"""

import sqlite3
import json
import time
from typing import Optional, Dict, Any
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
        """Create table if not exists."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS context (
                    context_type TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL,
                    metadata_json TEXT,
                    updated_at REAL NOT NULL
                )
            """)
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


# Global singleton
_context_store = None


def get_context_store() -> ContextStore:
    global _context_store
    if _context_store is None:
        _context_store = ContextStore()
    return _context_store
