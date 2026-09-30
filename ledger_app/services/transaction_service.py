from typing import Optional, List
from ledger_app.models.transaction import Transaction
from ledger_app.repositories.transaction_repository import TransactionRepository
from ledger_app.repositories.customer_repository import CustomerRepository
from ledger_app.repositories.payment_mode_repository import PaymentModeRepository

class TransactionService:
    """Handles business logic and validation for Transaction entities."""

    def __init__(self, transaction_repo: TransactionRepository, 
                 customer_repo: CustomerRepository,
                 payment_mode_repo: PaymentModeRepository):
        self.repo = transaction_repo
        self.customer_repo = customer_repo
        self.payment_mode_repo = payment_mode_repo

    def validate_transaction_data(self, customer_id: int, transaction_type: str, 
                                  amount: float, payment_mode_id: Optional[int]) -> None:
        """Validates transaction parameters before writing to the database."""
        # 1. Verify customer exists
        if not self.customer_repo.find_by_id(customer_id):
            raise ValueError(f"Customer with ID {customer_id} does not exist.")

        # 2. Check transaction type
        if transaction_type not in ('CREDIT', 'DEBIT', 'DAILY_CHARGE'):
            raise ValueError("Transaction type must be 'CREDIT', 'DEBIT', or 'DAILY_CHARGE'.")

        # 3. Check amount
        if amount <= 0:
            raise ValueError("Transaction amount must be greater than zero.")

        # 4. Check payment mode if provided
        if payment_mode_id is not None:
            if not self.payment_mode_repo.find_by_id(payment_mode_id):
                raise ValueError(f"Payment mode with ID {payment_mode_id} does not exist.")
            
        # 5. Enforce business rules: CREDIT transactions must specify a payment mode
        if transaction_type == 'CREDIT' and payment_mode_id is None:
            raise ValueError("Credit transactions (payments received) must specify a payment mode.")

    def record_transaction(self, customer_id: int, transaction_type: str, amount: float, 
                           payment_mode_id: Optional[int] = None, description: Optional[str] = None, 
                           transaction_date: Optional[str] = None) -> int:
        """
        Records a new transaction (debit, credit, or charge).
        Returns the ID of the recorded transaction.
        """
        self.validate_transaction_data(customer_id, transaction_type, amount, payment_mode_id)

        txn = Transaction(
            id=None,
            customer_id=customer_id,
            transaction_type=transaction_type,
            amount=float(amount),
            payment_mode_id=payment_mode_id,
            description=description.strip() if description else None,
            transaction_date=transaction_date
        )
        return self.repo.save(txn)

    def delete_transaction(self, txn_id: int) -> bool:
        """Deletes a transaction by ID."""
        txn = self.repo.find_by_id(txn_id)
        if not txn:
            raise ValueError(f"Transaction with ID {txn_id} does not exist.")
        return self.repo.delete(txn_id)

    def get_transaction(self, txn_id: int) -> Optional[Transaction]:
        """Retrieves a single transaction by ID."""
        return self.repo.find_by_id(txn_id)

    def list_transactions_by_customer(self, customer_id: int, start_date: Optional[str] = None, 
                                       end_date: Optional[str] = None) -> List[Transaction]:
        """Lists transactions for a customer, with optional date range filters."""
        if not self.customer_repo.find_by_id(customer_id):
            raise ValueError(f"Customer with ID {customer_id} does not exist.")
        return self.repo.find_by_customer(customer_id, start_date, end_date)
