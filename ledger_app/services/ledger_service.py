from typing import Optional, List, Dict, Any
from ledger_app.repositories.customer_repository import CustomerRepository
from ledger_app.repositories.transaction_repository import TransactionRepository

class LedgerService:
    """Manages business operations for calculating customer ledger details and running balances."""

    def __init__(self, customer_repo: CustomerRepository, transaction_repo: TransactionRepository):
        self.customer_repo = customer_repo
        self.txn_repo = transaction_repo

    def get_customer_ledger(self, customer_id: int, start_date: Optional[str] = None, 
                            end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates a comprehensive ledger statement for a customer.
        Includes customer metadata and chronological transactions with calculated running balances.
        """
        customer = self.customer_repo.find_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer with ID {customer_id} does not exist.")

        # Fetch joined transactions
        txns = self.txn_repo.get_ledger_rows(customer_id, start_date, end_date)

        # Calculate chronological running balances
        ledger_entries = []
        running_balance = customer.opening_balance

        # If we have a start date filter, the initial running balance must include transactions
        # prior to the start date. Let's calculate that initial balance accurately!
        if start_date:
            prior_txns = self.txn_repo.find_by_customer(customer_id, end_date=start_date)
            # Subtract or add amounts based on transaction type for all txns BEFORE start_date
            # Note: start_date is inclusive in get_ledger_rows, so we fetch strictly prior txns
            # Let's filter out the ones that are equal to start_date or handle it carefully.
            # A cleaner way is to compute running balance from the very beginning of all time,
            # and then filter the entries by date range. This keeps the math extremely robust!
            all_txns = self.txn_repo.get_ledger_rows(customer_id)
            for txn in all_txns:
                txn_type = txn['transaction_type']
                amount = txn['amount']
                if txn_type in ('DEBIT', 'DAILY_CHARGE'):
                    running_balance += amount
                elif txn_type == 'CREDIT':
                    running_balance -= amount
                
                # Check if it falls within our date range filters
                in_range = True
                if start_date and txn['transaction_date'] < start_date:
                    in_range = False
                if end_date and txn['transaction_date'] > end_date:
                    in_range = False

                if in_range:
                    txn_entry = dict(txn)
                    txn_entry['running_balance'] = round(running_balance, 2)
                    ledger_entries.append(txn_entry)
        else:
            for txn in txns:
                txn_type = txn['transaction_type']
                amount = txn['amount']
                if txn_type in ('DEBIT', 'DAILY_CHARGE'):
                    running_balance += amount
                elif txn_type == 'CREDIT':
                    running_balance -= amount
                
                txn_entry = dict(txn)
                txn_entry['running_balance'] = round(running_balance, 2)
                ledger_entries.append(txn_entry)

        # Summary statistics
        total_debits = sum(t['amount'] for t in ledger_entries if t['transaction_type'] in ('DEBIT', 'DAILY_CHARGE'))
        total_credits = sum(t['amount'] for t in ledger_entries if t['transaction_type'] == 'CREDIT')
        current_balance = self.customer_repo.get_customer_balance(customer_id)

        return {
            "customer": customer,
            "opening_balance": round(customer.opening_balance, 2),
            "current_balance": round(current_balance, 2),
            "total_debits": round(total_debits, 2),
            "total_credits": round(total_credits, 2),
            "transactions": ledger_entries
        }
