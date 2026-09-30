from typing import Optional, List, Dict, Any
from ledger_app.database.db_connection import DatabaseManager

class ReportService:
    """Provides reporting and analytical aggregations for the Ledger system."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def get_financial_summary(self, start_date: Optional[str] = None, 
                              end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates aggregate transactions totals (credit, debit, fees)
        and the net balance change in the specified time frame.
        """
        query = """
            SELECT 
                COALESCE(SUM(CASE WHEN transaction_type = 'DEBIT' THEN amount ELSE 0 END), 0) as total_debit,
                COALESCE(SUM(CASE WHEN transaction_type = 'CREDIT' THEN amount ELSE 0 END), 0) as total_credit,
                COALESCE(SUM(CASE WHEN transaction_type = 'DAILY_CHARGE' THEN amount ELSE 0 END), 0) as total_charges
            FROM transactions
        """
        conditions = []
        params = []

        if start_date:
            conditions.append("transaction_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("transaction_date <= ?")
            params.append(end_date)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            
            total_debit = float(row['total_debit'])
            total_credit = float(row['total_credit'])
            total_charges = float(row['total_charges'])
            
            # Net change in what customers owe us
            # (Debits and charges increase outstanding, credits decrease outstanding)
            net_change = (total_debit + total_charges) - total_credit

            return {
                "total_debit": round(total_debit, 2),
                "total_credit": round(total_credit, 2),
                "total_charges": round(total_charges, 2),
                "net_change": round(net_change, 2)
            }

    def get_date_range_report(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Lists all transactions across all customers within a date range.
        Includes Customer Name, Date, Description, Type, Payment Mode, and Amount.
        """
        query = """
            SELECT 
                t.id, t.transaction_date, c.name as customer_name, t.transaction_type, 
                t.amount, pm.mode_name, t.description
            FROM transactions t
            JOIN customers c ON t.customer_id = c.id
            LEFT JOIN payment_modes pm ON t.payment_mode_id = pm.id
            WHERE t.transaction_date >= ? AND t.transaction_date <= ?
            ORDER BY t.transaction_date DESC, t.id DESC;
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (start_date, end_date))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_monthly_report(self, year: str) -> List[Dict[str, Any]]:
        """
        Groups transaction aggregates by month for a given calendar year (YYYY format).
        Returns a summary list for each month (01 to 12).
        """
        query = """
            SELECT 
                strftime('%m', transaction_date) as month_num,
                COALESCE(SUM(CASE WHEN transaction_type = 'DEBIT' THEN amount ELSE 0 END), 0) as total_debit,
                COALESCE(SUM(CASE WHEN transaction_type = 'CREDIT' THEN amount ELSE 0 END), 0) as total_credit,
                COALESCE(SUM(CASE WHEN transaction_type = 'DAILY_CHARGE' THEN amount ELSE 0 END), 0) as total_charges
            FROM transactions
            WHERE strftime('%Y', transaction_date) = ?
            GROUP BY month_num
            ORDER BY month_num ASC;
        """
        months_map = {
            "01": "January", "02": "February", "03": "March", "04": "April",
            "05": "May", "06": "June", "07": "July", "08": "August",
            "09": "September", "10": "October", "11": "November", "12": "December"
        }

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (year,))
            rows = cursor.fetchall()
            
            # Seed all 12 months with empty values to avoid holes in data
            results = {num: {
                "month_num": num,
                "month_name": name,
                "total_debit": 0.0,
                "total_credit": 0.0,
                "total_charges": 0.0,
                "net_change": 0.0
            } for num, name in months_map.items()}

            for row in rows:
                month_num = row['month_num']
                if month_num in results:
                    td = float(row['total_debit'])
                    tc = float(row['total_credit'])
                    tch = float(row['total_charges'])
                    results[month_num].update({
                        "total_debit": round(td, 2),
                        "total_credit": round(tc, 2),
                        "total_charges": round(tch, 2),
                        "net_change": round((td + tch) - tc, 2)
                    })

            return list(results.values())

    def get_outstanding_balances_report(self) -> List[Dict[str, Any]]:
        """
        Lists all customers along with their current balance, sorted by outstanding debt descending.
        Only shows customers who have non-zero balances.
        """
        query = """
            SELECT 
                c.id, c.name, c.phone,
                (c.opening_balance + 
                 COALESCE(SUM(CASE WHEN t.transaction_type IN ('DEBIT', 'DAILY_CHARGE') THEN t.amount ELSE 0 END), 0) - 
                 COALESCE(SUM(CASE WHEN t.transaction_type = 'CREDIT' THEN t.amount ELSE 0 END), 0)) AS current_balance
            FROM customers c
            LEFT JOIN transactions t ON c.id = t.customer_id
            GROUP BY c.id
            HAVING current_balance != 0
            ORDER BY current_balance DESC;
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_todays_summary(self) -> Dict[str, Any]:
        """
        Aggregates counts and values of transactions recorded on the current calendar date.
        """
        query = """
            SELECT 
                COUNT(*) as count,
                COALESCE(SUM(CASE WHEN transaction_type = 'DEBIT' THEN amount ELSE 0 END), 0) as total_debit,
                COALESCE(SUM(CASE WHEN transaction_type = 'CREDIT' THEN amount ELSE 0 END), 0) as total_credit,
                COALESCE(SUM(CASE WHEN transaction_type = 'DAILY_CHARGE' THEN amount ELSE 0 END), 0) as total_charges
            FROM transactions
            WHERE date(transaction_date) = date('now', 'localtime');
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            row = cursor.fetchone()
            
            t_debit = float(row["total_debit"])
            t_credit = float(row["total_credit"])
            t_charges = float(row["total_charges"])
            
            return {
                "count": int(row["count"]),
                "total_debit": round(t_debit, 2),
                "total_credit": round(t_credit, 2),
                "total_charges": round(t_charges, 2),
                "net_change": round((t_debit + t_charges) - t_credit, 2)
            }
