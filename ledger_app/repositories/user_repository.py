from typing import Optional, List, Dict, Any
from ledger_app.repositories.base_repository import BaseRepository
from ledger_app.models.user import User


class UserRepository(BaseRepository):
    """
    Repository for the `users` table.
    Hash/salt fields are only exposed in raw-credential methods;
    the User domain model never carries them.
    """

    # ── Read Operations ───────────────────────────────────────────────────────

    def find_by_username(self, username: str) -> Optional[User]:
        """Case-insensitive username lookup."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, role, is_active, created_at, last_login, must_change, recovery_email "
                "FROM users WHERE username = ? COLLATE NOCASE;",
                (username,)
            )
            row = cursor.fetchone()
            return User.from_row(row) if row else None

    def find_by_id(self, user_id: int) -> Optional[User]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, role, is_active, created_at, last_login, must_change, recovery_email "
                "FROM users WHERE id = ?;",
                (user_id,)
            )
            row = cursor.fetchone()
            return User.from_row(row) if row else None

    def find_all(self) -> List[User]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, role, is_active, created_at, last_login, must_change, recovery_email "
                "FROM users ORDER BY role DESC, username ASC;"  # owners first
            )
            return [User.from_row(r) for r in cursor.fetchall()]

    def update_recovery_email(self, user_id: int, email: str) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET recovery_email = ? WHERE id = ?;",
                (email, user_id)
            )
            return cursor.rowcount > 0

    def increment_otp_attempts(self, username: str) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET otp_attempts = otp_attempts + 1 WHERE username = ? COLLATE NOCASE;",
                (username,)
            )
            cursor.execute(
                "SELECT otp_attempts FROM users WHERE username = ? COLLATE NOCASE;",
                (username,)
            )
            row = cursor.fetchone()
            return row["otp_attempts"] if row else 0

    def reset_otp_attempts(self, username: str) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET otp_attempts = 0 WHERE username = ? COLLATE NOCASE;",
                (username,)
            )
            return cursor.rowcount > 0

    def set_last_recovery_request(self, username: str, timestamp: str) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET last_recovery_request = ? WHERE username = ? COLLATE NOCASE;",
                (timestamp, username)
            )
            return cursor.rowcount > 0

    def set_must_change(self, user_id: int, must_change: bool) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET must_change = ? WHERE id = ?;",
                (1 if must_change else 0, user_id)
            )
            return cursor.rowcount > 0

    def get_recovery_info(self, username: str) -> Optional[dict]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, role, recovery_email, otp_attempts, last_recovery_request, must_change "
                "FROM users WHERE username = ? COLLATE NOCASE;",
                (username,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "role": row["role"],
                    "recovery_email": row["recovery_email"],
                    "otp_attempts": row["otp_attempts"],
                    "last_recovery_request": row["last_recovery_request"],
                    "must_change": bool(row["must_change"]),
                }
            return None

    def get_user_count(self) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE is_active = 1;")
            return int(cursor.fetchone()["cnt"])

    def username_exists(self, username: str, exclude_id: Optional[int] = None) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if exclude_id:
                cursor.execute(
                    "SELECT 1 FROM users WHERE username = ? COLLATE NOCASE AND id != ?;",
                    (username, exclude_id)
                )
            else:
                cursor.execute(
                    "SELECT 1 FROM users WHERE username = ? COLLATE NOCASE;",
                    (username,)
                )
            return cursor.fetchone() is not None

    # ── Credential Methods (raw hash access) ──────────────────────────────────

    def get_credentials(self, username: str) -> Optional[Dict[str, str]]:
        """Returns {'id', 'password_hash', 'salt', 'is_active'} for the given username or None."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, password_hash, salt, is_active FROM users "
                "WHERE username = ? COLLATE NOCASE;",
                (username,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "id":            row["id"],
                    "password_hash": row["password_hash"],
                    "salt":          row["salt"],
                    "is_active":     bool(row["is_active"]),
                }
            return None

    def get_credentials_by_id(self, user_id: int) -> Optional[Dict[str, str]]:
        """Returns {'id', 'password_hash', 'salt'} by user ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, password_hash, salt FROM users WHERE id = ?;",
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "id":            row["id"],
                    "password_hash": row["password_hash"],
                    "salt":          row["salt"],
                }
            return None

    def get_pin_credentials(self, user_id: int) -> Optional[Dict[str, str]]:
        """Returns {'pin_hash', 'pin_salt'} or None if no PIN is set."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT pin_hash, pin_salt FROM users WHERE id = ?;",
                (user_id,)
            )
            row = cursor.fetchone()
            if row and row["pin_hash"]:
                return {"pin_hash": row["pin_hash"], "pin_salt": row["pin_salt"]}
            return None

    # ── Write Operations ──────────────────────────────────────────────────────

    def create(self, username: str, password_hash: str, salt: str, role: str) -> int:
        """Inserts a new user. Returns the new row ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password_hash, salt, role) VALUES (?, ?, ?, ?);",
                (username, password_hash, salt, role)
            )
            return cursor.lastrowid

    def update_password(self, user_id: int, password_hash: str, salt: str) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?;",
                (password_hash, salt, user_id)
            )
            return cursor.rowcount > 0

    def update_pin(self, user_id: int, pin_hash: Optional[str], pin_salt: Optional[str]) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET pin_hash = ?, pin_salt = ? WHERE id = ?;",
                (pin_hash, pin_salt, user_id)
            )
            return cursor.rowcount > 0

    def update_username(self, user_id: int, new_username: str) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET username = ? WHERE id = ?;",
                (new_username, user_id)
            )
            return cursor.rowcount > 0

    def update_role(self, user_id: int, new_role: str) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET role = ? WHERE id = ?;",
                (new_role, user_id)
            )
            return cursor.rowcount > 0

    def set_active(self, user_id: int, is_active: bool) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET is_active = ? WHERE id = ?;",
                (1 if is_active else 0, user_id)
            )
            return cursor.rowcount > 0

    def update_last_login(self, user_id: int) -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                "UPDATE users SET last_login = datetime('now', 'localtime') WHERE id = ?;",
                (user_id,)
            )

    def delete(self, user_id: int) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?;", (user_id,))
            return cursor.rowcount > 0
