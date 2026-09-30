import re
from typing import Optional, List, Dict, Any
from ledger_app.models.customer import Customer, BUILTIN_TAGS
from ledger_app.repositories.customer_repository import CustomerRepository

class CustomerService:
    """Handles business logic and validation for Customer entities."""

    def __init__(self, customer_repo: CustomerRepository):
        self.repo = customer_repo

    def validate_customer_data(self, name: str, phone: Optional[str]) -> None:
        """Validates customer parameters before insertion or update."""
        if not name or len(name.strip()) < 2:
            raise ValueError("Customer name must be at least 2 characters long.")

        if phone:
            phone_clean = re.sub(r'\D', '', phone)  # Remove non-numeric characters
            if len(phone_clean) < 10 or len(phone_clean) > 15:
                raise ValueError("Phone number must contain between 10 and 15 digits.")

    def create_customer(self, name: str, phone: Optional[str] = None,
                        address: Optional[str] = None, notes: Optional[str] = None,
                        opening_balance: float = 0.0,
                        customer_tag: str = "General") -> int:
        """
        Creates a new customer. Enforces validation.
        Returns the ID of the newly created customer.
        """
        self.validate_customer_data(name, phone)
        
        # Clean phone format
        clean_phone = re.sub(r'\D', '', phone) if phone else None
        
        customer = Customer(
            id=None,
            name=name.strip(),
            phone=clean_phone,
            address=address.strip() if address else None,
            notes=notes.strip() if notes else None,
            opening_balance=float(opening_balance),
            customer_tag=customer_tag.strip() if customer_tag else "General"
        )
        return self.repo.save(customer)

    def update_customer(self, customer_id: int, name: str, phone: Optional[str] = None,
                        address: Optional[str] = None, notes: Optional[str] = None,
                        opening_balance: float = 0.0,
                        customer_tag: str = "General") -> bool:
        """
        Updates an existing customer. Enforces validation.
        Returns True if successful, False otherwise.
        """
        existing = self.repo.find_by_id(customer_id)
        if not existing:
            raise ValueError(f"Customer with ID {customer_id} does not exist.")

        self.validate_customer_data(name, phone)
        
        clean_phone = re.sub(r'\D', '', phone) if phone else None

        updated_customer = Customer(
            id=customer_id,
            name=name.strip(),
            phone=clean_phone,
            address=address.strip() if address else None,
            notes=notes.strip() if notes else None,
            opening_balance=float(opening_balance),
            customer_tag=customer_tag.strip() if customer_tag else "General"
        )
        return self.repo.save(updated_customer) == customer_id

    def delete_customer(self, customer_id: int) -> bool:
        """Deletes a customer by ID."""
        if not self.repo.find_by_id(customer_id):
            raise ValueError(f"Customer with ID {customer_id} does not exist.")
        return self.repo.delete(customer_id)

    def get_customer_by_id(self, customer_id: int) -> Optional[Customer]:
        """Retrieves a customer by ID."""
        return self.repo.find_by_id(customer_id)

    def list_customers(
        self,
        search_query: str = "",
        balance_filter: Optional[str] = None,
        tag_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Lists all customers with their calculated balances.
        Optional filters:
          - balance_filter: 'DEBTORS' | 'CREDITORS'
          - tag_filter    : tag string e.g. 'VIP', 'Retail'  (None or 'All' = no filter)
        """
        if balance_filter and balance_filter.upper() not in ('DEBTORS', 'CREDITORS'):
            balance_filter = None

        # Normalise tag filter
        resolved_tag = None
        if tag_filter and tag_filter.upper() not in ("ALL", "ALL CUSTOMERS"):
            resolved_tag = tag_filter
        
        return self.repo.get_all_with_balances(
            search_query=search_query.strip(),
            balance_filter=balance_filter,
            tag_filter=resolved_tag
        )

    def get_customer_balance(self, customer_id: int) -> float:
        """Computes current outstanding balance for a customer."""
        return self.repo.get_customer_balance(customer_id)

    def get_customer_counts_by_tag(self) -> Dict[str, int]:
        """Returns customer count grouped by tag label."""
        return self.repo.get_customer_counts_by_tag()
