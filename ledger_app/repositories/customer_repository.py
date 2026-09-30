from typing import Optional, List, Dict, Any
from ledger_app.repositories.base_repository import BaseRepository
from ledger_app.models.customer import Customer

class CustomerRepository(BaseRepository):
    """Repository managing sqlite operations on the customers table."""

    def find_all(self, search_query: str = "") -> List[Customer]:
        """Retrieves all customers, optionally filtering by name or phone."""
        if search_query:
            query = """
                SELECT id, name, phone, address, notes, opening_balance, customer_tag, created_at
                FROM customers
                WHERE name LIKE ? OR phone LIKE ?
                ORDER BY name ASC;
            """
            params = (f"%{search_query}%", f"%{search_query}%")
        else:
            query = """
                SELECT id, name, phone, address, notes, opening_balance, customer_tag, created_at
                FROM customers
                ORDER BY name ASC;
            """
            params = ()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [Customer.from_row(row) for row in rows]

    def find_by_id(self, customer_id: int) -> Optional[Customer]:
        """Retrieves a specific customer by ID."""
        query = """
            SELECT id, name, phone, address, notes, opening_balance, customer_tag, created_at
            FROM customers
            WHERE id = ?;
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (customer_id,))
            row = cursor.fetchone()
            if row:
                return Customer.from_row(row)
            return None

    def save(self, customer: Customer) -> int:
        """
        Saves a customer record (inserts if id is None, updates otherwise).
        Returns the ID of the saved customer.
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if customer.id is None:
                query = """
                    INSERT INTO customers (name, phone, address, notes, opening_balance, customer_tag)
                    VALUES (?, ?, ?, ?, ?, ?);
                """
                cursor.execute(query, (
                    customer.name,
                    customer.phone,
                    customer.address,
                    customer.notes,
                    customer.opening_balance,
                    customer.customer_tag
                ))
                customer.id = cursor.lastrowid
            else:
                query = """
                    UPDATE customers
                    SET name = ?, phone = ?, address = ?, notes = ?, opening_balance = ?, customer_tag = ?
                    WHERE id = ?;
                """
                cursor.execute(query, (
                    customer.name,
                    customer.phone,
                    customer.address,
                    customer.notes,
                    customer.opening_balance,
                    customer.customer_tag,
                    customer.id
                ))
            return customer.id

    def delete(self, customer_id: int) -> bool:
        """Deletes a customer by ID. Due to CASCADE constraint, transactions are also deleted."""
        query = "DELETE FROM customers WHERE id = ?;"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (customer_id,))
            return cursor.rowcount > 0

    def get_customer_balance(self, customer_id: int) -> float:
        """
        Computes the current outstanding balance for a customer.
        Formula: opening_balance + sum(DEBIT) + sum(DAILY_CHARGE) - sum(CREDIT)
        """
        query = """
            SELECT 
                c.opening_balance + 
                COALESCE(SUM(CASE WHEN t.transaction_type IN ('DEBIT', 'DAILY_CHARGE') THEN t.amount ELSE 0 END), 0) - 
                COALESCE(SUM(CASE WHEN t.transaction_type = 'CREDIT' THEN t.amount ELSE 0 END), 0) AS balance
            FROM customers c
            LEFT JOIN transactions t ON c.id = t.customer_id
            WHERE c.id = ?
            GROUP BY c.id;
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (customer_id,))
            row = cursor.fetchone()
            if row:
                return float(row['balance'])
            
            # If customer has no transactions and was found, return opening balance
            customer = self.find_by_id(customer_id)
            return customer.opening_balance if customer else 0.0

    def get_all_with_balances(
        self,
        search_query: str = "",
        balance_filter: Optional[str] = None,
        tag_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves all customers with their calculated balances.
        Supports filtering by:
          - search_query  : name / phone substring
          - balance_filter: 'DEBTORS' (balance > 0), 'CREDITORS' (balance < 0)
          - tag_filter    : exact tag string e.g. 'VIP', 'Retail'
        """
        query = """
            SELECT 
                c.id, c.name, c.phone, c.address, c.notes,
                c.opening_balance, c.customer_tag, c.created_at,
                (c.opening_balance + 
                 COALESCE(SUM(CASE WHEN t.transaction_type IN ('DEBIT', 'DAILY_CHARGE') THEN t.amount ELSE 0 END), 0) - 
                 COALESCE(SUM(CASE WHEN t.transaction_type = 'CREDIT' THEN t.amount ELSE 0 END), 0)) AS current_balance
            FROM customers c
            LEFT JOIN transactions t ON c.id = t.customer_id
        """
        
        conditions = []
        params = []
        
        if search_query:
            conditions.append("(c.name LIKE ? OR c.phone LIKE ?)")
            params.extend([f"%{search_query}%", f"%{search_query}%"])

        if tag_filter and tag_filter.upper() != "ALL":
            conditions.append("c.customer_tag = ?")
            params.append(tag_filter)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " GROUP BY c.id"
        
        # Add HAVING clause for balance filter
        if balance_filter:
            if balance_filter.upper() == 'DEBTORS':
                query += " HAVING current_balance > 0"
            elif balance_filter.upper() == 'CREDITORS':
                query += " HAVING current_balance < 0"
                
        query += " ORDER BY c.name ASC;"

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_customer_counts_by_tag(self) -> Dict[str, int]:
        """Returns a dict mapping each tag to its customer count."""
        query = """
            SELECT customer_tag, COUNT(*) as count
            FROM customers
            GROUP BY customer_tag
            ORDER BY count DESC;
        """
        result = {}
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            for row in cursor.fetchall():
                result[row['customer_tag']] = int(row['count'])
        return result
