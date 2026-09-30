import datetime
from typing import List, Dict, Any, Optional
from ledger_app.database.db_connection import DatabaseManager

class AnalyticsService:
    """Provides reporting aggregations for plotting Matplotlib analytics."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def _get_last_12_months_list(self) -> List[str]:
        """Returns the list of the last 12 months in YYYY-MM format chronologically."""
        now = datetime.datetime.now()
        months = []
        for i in range(11, -1, -1):
            m = now.month - i
            y = now.year
            while m <= 0:
                m += 12
                y -= 1
            months.append(f"{y:04d}-{m:02d}")
        return months

    def get_monthly_credit_vs_debit(self) -> Dict[str, Any]:
        """
        Retrieves sum of credits and debits grouped by month for the last 12 months.
        """
        months = self._get_last_12_months_list()
        start_month = months[0]
        # First day of the start month
        start_date = f"{start_month}-01 00:00:00"

        query = """
            SELECT 
                strftime('%Y-%m', transaction_date) as yr_mo,
                SUM(CASE WHEN transaction_type IN ('DEBIT', 'DAILY_CHARGE') THEN amount ELSE 0 END) as total_debit,
                SUM(CASE WHEN transaction_type = 'CREDIT' THEN amount ELSE 0 END) as total_credit
            FROM transactions
            WHERE transaction_date >= ?
            GROUP BY yr_mo;
        """

        data_map = {}
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (start_date,))
            rows = cursor.fetchall()
            for row in rows:
                data_map[row['yr_mo']] = {
                    "debit": float(row['total_debit']),
                    "credit": float(row['total_credit'])
                }

        # Format output mapping missing months to 0
        result = []
        for mo in months:
            vals = data_map.get(mo, {"debit": 0.0, "credit": 0.0})
            # Convert to pretty month name, e.g. "Jun 2026"
            dt = datetime.datetime.strptime(mo, "%Y-%m")
            label = dt.strftime("%b %y")
            result.append({
                "month_key": mo,
                "label": label,
                "debit": vals["debit"],
                "credit": vals["credit"]
            })
        return result

    def get_top_customers_by_balance(self) -> List[Dict[str, Any]]:
        """
        Retrieves the top 10 customers sorted by outstanding balance descending.
        """
        query = """
            SELECT 
                c.id, c.name,
                (c.opening_balance + 
                 COALESCE(SUM(CASE WHEN t.transaction_type IN ('DEBIT', 'DAILY_CHARGE') THEN t.amount ELSE 0 END), 0) - 
                 COALESCE(SUM(CASE WHEN t.transaction_type = 'CREDIT' THEN t.amount ELSE 0 END), 0)) as balance
            FROM customers c
            LEFT JOIN transactions t ON c.id = t.customer_id
            GROUP BY c.id
            ORDER BY balance DESC
            LIMIT 10;
        """
        result = []
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            for row in rows:
                result.append({
                    "id": row['id'],
                    "name": row['name'],
                    "balance": float(row['balance'])
                })
        return result

    def get_receivable_vs_payable(self) -> Dict[str, float]:
        """
        Calculates total Receivable (positive balances) and total Payable (negative balances).
        """
        query = """
            SELECT 
                c.id,
                (c.opening_balance + 
                 COALESCE(SUM(CASE WHEN t.transaction_type IN ('DEBIT', 'DAILY_CHARGE') THEN t.amount ELSE 0 END), 0) - 
                 COALESCE(SUM(CASE WHEN t.transaction_type = 'CREDIT' THEN t.amount ELSE 0 END), 0)) as balance
            FROM customers c
            LEFT JOIN transactions t ON c.id = t.customer_id
            GROUP BY c.id;
        """
        receivable = 0.0
        payable = 0.0
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            for row in rows:
                bal = float(row['balance'])
                if bal > 0:
                    receivable += bal
                elif bal < 0:
                    payable += abs(bal)
        return {
            "receivable": round(receivable, 2),
            "payable": round(payable, 2)
        }

    def get_monthly_transaction_count(self) -> List[Dict[str, Any]]:
        """
        Retrieves number of transactions per month for the last 12 months.
        """
        months = self._get_last_12_months_list()
        start_month = months[0]
        start_date = f"{start_month}-01 00:00:00"

        query = """
            SELECT 
                strftime('%Y-%m', transaction_date) as yr_mo,
                COUNT(*) as count
            FROM transactions
            WHERE transaction_date >= ?
            GROUP BY yr_mo;
        """

        data_map = {}
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (start_date,))
            rows = cursor.fetchall()
            for row in rows:
                data_map[row['yr_mo']] = int(row['count'])

        result = []
        for mo in months:
            count = data_map.get(mo, 0)
            dt = datetime.datetime.strptime(mo, "%Y-%m")
            label = dt.strftime("%b %y")
            result.append({
                "month_key": mo,
                "label": label,
                "count": count
            })
        return result

    def get_customer_analytics_data(self, customer_id: int) -> Dict[str, Any]:
        """
        Fetches detailed credit history trend, debit history trend, running balance trend,
        and payment mode breakdown for a single customer.
        """
        # 1. Fetch customer opening balance
        open_bal = 0.0
        cust_name = ""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, opening_balance FROM customers WHERE id = ?;", (customer_id,))
            row = cursor.fetchone()
            if row:
                cust_name = row['name']
                open_bal = float(row['opening_balance'])

        # 2. Fetch all transactions chronologically
        query_txns = """
            SELECT transaction_date, transaction_type, amount,
                   (CASE WHEN transaction_type IN ('DEBIT', 'DAILY_CHARGE') THEN amount ELSE -amount END) as signed_amt
            FROM transactions
            WHERE customer_id = ?
            ORDER BY transaction_date ASC, id ASC;
        """

        credit_history = []
        debit_history = []
        running_history = []

        # Add initial point for running balance
        running_history.append({
            "date": "Opening",
            "balance": open_bal
        })

        current_balance = open_bal

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query_txns, (customer_id,))
            rows = cursor.fetchall()
            for row in rows:
                date_str = row['transaction_date'][:10] # YYYY-MM-DD
                amt = float(row['amount'])
                signed_amt = float(row['signed_amt'])
                txn_type = row['transaction_type']

                # Categorize history
                if txn_type == 'CREDIT':
                    credit_history.append({
                        "date": date_str,
                        "amount": amt
                    })
                else:
                    debit_history.append({
                        "date": date_str,
                        "amount": amt
                    })

                current_balance += signed_amt
                running_history.append({
                    "date": date_str,
                    "balance": current_balance
                })

        # 3. Payment Mode Breakdown
        query_modes = """
            SELECT pm.mode_name, SUM(t.amount) as total_amount
            FROM transactions t
            JOIN payment_modes pm ON t.payment_mode_id = pm.id
            WHERE t.customer_id = ? AND t.transaction_type = 'CREDIT'
            GROUP BY pm.mode_name;
        """

        modes_breakdown = {}
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query_modes, (customer_id,))
            rows = cursor.fetchall()
            for row in rows:
                modes_breakdown[row['mode_name']] = float(row['total_amount'])

        return {
            "customer_name": cust_name,
            "credit_history": credit_history,
            "debit_history": debit_history,
            "running_history": running_history,
            "payment_mode_breakdown": modes_breakdown
        }

    def get_customer_tag_distribution(self) -> List[Dict[str, Any]]:
        """
        Returns the count of customers per tag, ordered by count descending.
        Used by the Dashboard Category Breakdown section.
        """
        query = """
            SELECT customer_tag, COUNT(*) as count
            FROM customers
            GROUP BY customer_tag
            ORDER BY count DESC;
        """
        result = []
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            for row in cursor.fetchall():
                result.append({
                    "tag": row['customer_tag'],
                    "count": int(row['count'])
                })
        return result

    def get_top_customers_by_tag(self, tag: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Returns top customers within a given tag, sorted by outstanding balance descending.
        Used by the Analytics tab's per-category breakdown.
        """
        query = """
            SELECT
                c.id, c.name, c.customer_tag,
                (c.opening_balance +
                 COALESCE(SUM(CASE WHEN t.transaction_type IN ('DEBIT', 'DAILY_CHARGE') THEN t.amount ELSE 0 END), 0) -
                 COALESCE(SUM(CASE WHEN t.transaction_type = 'CREDIT' THEN t.amount ELSE 0 END), 0)) AS balance
            FROM customers c
            LEFT JOIN transactions t ON c.id = t.customer_id
            WHERE c.customer_tag = ?
            GROUP BY c.id
            ORDER BY balance DESC
            LIMIT ?;
        """
        result = []
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (tag, limit))
            for row in cursor.fetchall():
                result.append({
                    "id": row['id'],
                    "name": row['name'],
                    "tag": row['customer_tag'],
                    "balance": float(row['balance'])
                })
        return result

