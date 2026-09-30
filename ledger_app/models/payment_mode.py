from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class PaymentMode:
    id: Optional[int]
    mode_name: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_row(cls, row) -> 'PaymentMode':
        """Constructs a PaymentMode object from an sqlite3.Row or dict."""
        row_dict = dict(row)
        return cls(
            id=row_dict.get('id'),
            mode_name=row_dict.get('mode_name')
        )
