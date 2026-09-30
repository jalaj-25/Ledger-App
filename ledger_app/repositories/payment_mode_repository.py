from typing import Optional, List
from ledger_app.repositories.base_repository import BaseRepository
from ledger_app.models.payment_mode import PaymentMode

class PaymentModeRepository(BaseRepository):
    """Repository managing sqlite operations on the payment_modes table."""

    def find_all(self) -> List[PaymentMode]:
        """Retrieves all payment modes ordered by mode_name."""
        query = "SELECT id, mode_name FROM payment_modes ORDER BY mode_name ASC;"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            return [PaymentMode.from_row(row) for row in rows]

    def find_by_id(self, mode_id: int) -> Optional[PaymentMode]:
        """Retrieves a specific payment mode by its ID."""
        query = "SELECT id, mode_name FROM payment_modes WHERE id = ?;"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (mode_id,))
            row = cursor.fetchone()
            if row:
                return PaymentMode.from_row(row)
            return None

    def find_by_name(self, mode_name: str) -> Optional[PaymentMode]:
        """Retrieves a specific payment mode by its exact name (case-insensitive)."""
        query = "SELECT id, mode_name FROM payment_modes WHERE LOWER(mode_name) = LOWER(?);"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (mode_name,))
            row = cursor.fetchone()
            if row:
                return PaymentMode.from_row(row)
            return None

    def save(self, mode: PaymentMode) -> int:
        """
        Saves a payment mode (inserts if id is None, updates otherwise).
        Returns the ID of the saved payment mode.
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if mode.id is None:
                query = "INSERT INTO payment_modes (mode_name) VALUES (?);"
                cursor.execute(query, (mode.mode_name,))
                mode.id = cursor.lastrowid
            else:
                query = "UPDATE payment_modes SET mode_name = ? WHERE id = ?;"
                cursor.execute(query, (mode.mode_name, mode.id))
            return mode.id

    def delete(self, mode_id: int) -> bool:
        """Deletes a payment mode by its ID. Returns True if deleted, False otherwise."""
        query = "DELETE FROM payment_modes WHERE id = ?;"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (mode_id,))
            return cursor.rowcount > 0
