from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class Transaction:
    id: Optional[int]
    customer_id: int
    transaction_type: str  # 'CREDIT', 'DEBIT', or 'DAILY_CHARGE'
    amount: float
    payment_mode_id: Optional[int]
    description: Optional[str]
    transaction_date: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_row(cls, row) -> 'Transaction':
        """Constructs a Transaction object from an sqlite3.Row or dict."""
        row_dict = dict(row)
        return cls(
            id=row_dict.get('id'),
            customer_id=row_dict.get('customer_id'),
            transaction_type=row_dict.get('transaction_type'),
            amount=row_dict.get('amount'),
            payment_mode_id=row_dict.get('payment_mode_id'),
            description=row_dict.get('description'),
            transaction_date=row_dict.get('transaction_date')
        )
