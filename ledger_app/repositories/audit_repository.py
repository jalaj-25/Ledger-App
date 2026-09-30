from typing import List, Dict, Any, Optional
from ledger_app.repositories.base_repository import BaseRepository


class AuditRepository(BaseRepository):
    """Repository for the `audit_logs` table."""

    def log(
        self,
        action: str,
        details: str = "",
        user_id: Optional[int] = None,
        username: str = "system"
    ) -> None:
        """Inserts one audit log entry. Never raises — failures are printed."""
        try:
            with self.db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO audit_logs (user_id, username, action, details)
                    VALUES (?, ?, ?, ?);
                    """,
                    (user_id, username, action, details or "")
                )
        except Exception as e:
            print(f"[AuditLog] Failed to write log: {e}")

    def get_recent(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Returns the most recent N audit log entries, newest first."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, username, action, details, timestamp
                FROM audit_logs
                ORDER BY timestamp DESC
                LIMIT ?;
                """,
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_by_user(self, user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Returns audit log entries for a specific user."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, username, action, details, timestamp
                FROM audit_logs
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?;
                """,
                (user_id, limit)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_by_action(self, action: str, limit: int = 100) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, username, action, details, timestamp
                FROM audit_logs
                WHERE action = ?
                ORDER BY timestamp DESC
                LIMIT ?;
                """,
                (action, limit)
            )
            return [dict(row) for row in cursor.fetchall()]
