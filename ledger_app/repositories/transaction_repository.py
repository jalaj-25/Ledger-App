from typing import Optional, List, Dict, Any
from ledger_app.repositories.base_repository import BaseRepository
from ledger_app.models.transaction import Transaction

class TransactionRepository(BaseRepository):
    """Repository managing sqlite operations on the transactions table."""

    def find_all(self) -> List[Transaction]:
        """Retrieves all transactions in the system."""
        query = """
            SELECT id, customer_id, transaction_type, amount, payment_mode_id, description, transaction_date
            FROM transactions
            ORDER BY transaction_date DESC;
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            return [Transaction.from_row(row) for row in rows]

    def find_by_id(self, txn_id: int) -> Optional[Transaction]:
        """Retrieves a single transaction by ID."""
        query = """
            SELECT id, customer_id, transaction_type, amount, payment_mode_id, description, transaction_date
            FROM transactions
            WHERE id = ?;
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (txn_id,))
            row = cursor.fetchone()
            if row:
                return Transaction.from_row(row)
            return None

    def find_by_customer(self, customer_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Transaction]:
        """Retrieves all transactions for a customer, with optional date filters."""
        query = """
            SELECT id, customer_id, transaction_type, amount, payment_mode_id, description, transaction_date
            FROM transactions
            WHERE customer_id = ?
        """
        params = [customer_id]

        if start_date:
            query += " AND transaction_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND transaction_date <= ?"
            params.append(end_date)

        query += " ORDER BY transaction_date ASC, id ASC;"

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [Transaction.from_row(row) for row in rows]

    def save(self, transaction: Transaction) -> int:
        """
        Saves a transaction record (inserts if id is None, updates otherwise).
        Returns the ID of the saved transaction.
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if transaction.id is None:
                if transaction.transaction_date:
                    query = """
                        INSERT INTO transactions (customer_id, transaction_type, amount, payment_mode_id, description, transaction_date)
                        VALUES (?, ?, ?, ?, ?, ?);
                    """
                    cursor.execute(query, (
                        transaction.customer_id,
                        transaction.transaction_type,
                        transaction.amount,
                        transaction.payment_mode_id,
                        transaction.description,
                        transaction.transaction_date
                    ))
                else:
                    query = """
                        INSERT INTO transactions (customer_id, transaction_type, amount, payment_mode_id, description)
                        VALUES (?, ?, ?, ?, ?);
                    """
                    cursor.execute(query, (
                        transaction.customer_id,
                        transaction.transaction_type,
                        transaction.amount,
                        transaction.payment_mode_id,
                        transaction.description
                    ))
                transaction.id = cursor.lastrowid
            else:
                if transaction.transaction_date:
                    query = """
                        UPDATE transactions
                        SET customer_id = ?, transaction_type = ?, amount = ?, payment_mode_id = ?, description = ?, transaction_date = ?
                        WHERE id = ?;
                    """
                    cursor.execute(query, (
                        transaction.customer_id,
                        transaction.transaction_type,
                        transaction.amount,
                        transaction.payment_mode_id,
                        transaction.description,
                        transaction.transaction_date,
                        transaction.id
                    ))
                else:
                    query = """
                        UPDATE transactions
                        SET customer_id = ?, transaction_type = ?, amount = ?, payment_mode_id = ?, description = ?
                        WHERE id = ?;
                    """
                    cursor.execute(query, (
                        transaction.customer_id,
                        transaction.transaction_type,
                        transaction.amount,
                        transaction.payment_mode_id,
                        transaction.description,
                        transaction.id
                    ))
            return transaction.id

    def delete(self, txn_id: int) -> bool:
        """Deletes a transaction by ID. Returns True if deleted, False otherwise."""
        query = "DELETE FROM transactions WHERE id = ?;"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (txn_id,))
            return cursor.rowcount > 0

    def get_ledger_rows(self, customer_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves a detailed list of transactions for a customer, including joined
        payment mode names. This is optimized for display.
        """
        query = """
            SELECT 
                t.id, t.customer_id, t.transaction_type, t.amount, 
                t.payment_mode_id, pm.mode_name, t.description, t.transaction_date
            FROM transactions t
            LEFT JOIN payment_modes pm ON t.payment_mode_id = pm.id
            WHERE t.customer_id = ?
        """
        params = [customer_id]

        if start_date:
            query += " AND t.transaction_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND t.transaction_date <= ?"
            params.append(end_date)

        query += " ORDER BY t.transaction_date ASC, t.id ASC;"

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
