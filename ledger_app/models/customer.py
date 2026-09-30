from dataclasses import dataclass, asdict
from typing import Optional

# Built-in tag options shown in the UI dropdown
BUILTIN_TAGS = ["General", "Retail", "Wholesale", "VIP", "Supplier", "Family"]

@dataclass
class Customer:
    id: Optional[int]
    name: str
    phone: Optional[str]
    address: Optional[str]
    notes: Optional[str]
    opening_balance: float
    customer_tag: str = "General"
    created_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_row(cls, row) -> 'Customer':
        """Constructs a Customer object from an sqlite3.Row or dict."""
        row_dict = dict(row)
        return cls(
            id=row_dict.get('id'),
            name=row_dict.get('name'),
            phone=row_dict.get('phone'),
            address=row_dict.get('address'),
            notes=row_dict.get('notes'),
            opening_balance=row_dict.get('opening_balance', 0.0),
            customer_tag=row_dict.get('customer_tag', 'General') or 'General',
            created_at=row_dict.get('created_at')
        )
