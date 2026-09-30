import os
import sys

# Add the current directory to sys.path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from ledger_app.database.db_connection import DatabaseManager
from ledger_app.models.customer import Customer
from ledger_app.models.transaction import Transaction
from ledger_app.models.payment_mode import PaymentMode
from ledger_app.repositories.customer_repository import CustomerRepository
from ledger_app.repositories.payment_mode_repository import PaymentModeRepository
from ledger_app.repositories.transaction_repository import TransactionRepository

def run_tests():
    db_file = "test_ledger.db"
    
    # Clean up previous test database
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"Removed existing test database: {db_file}")

    print("Initializing DatabaseManager...")
    db_manager = DatabaseManager(db_path=db_file)

    # Initialize repositories
    customer_repo = CustomerRepository(db_manager)
    payment_mode_repo = PaymentModeRepository(db_manager)
    txn_repo = TransactionRepository(db_manager)

    print("\n--- Testing Payment Modes Seeding ---")
    modes = payment_mode_repo.find_all()
    for mode in modes:
        print(f"Seeded Mode: ID={mode.id}, Name='{mode.mode_name}'")
    assert len(modes) > 0, "Payment modes should be seeded automatically!"

    print("\n--- Testing Customer Creation ---")
    c1 = Customer(
        id=None,
        name="Alice Smith",
        phone="1234567890",
        address="123 Maple Street",
        notes="First test customer",
        opening_balance=100.0
    )
    c2 = Customer(
        id=None,
        name="Bob Jones",
        phone="0987654321",
        address="456 Oak Ave",
        notes="Second test customer",
        opening_balance=0.0
    )

    c1_id = customer_repo.save(c1)
    c2_id = customer_repo.save(c2)
    print(f"Created Alice with ID: {c1_id}")
    print(f"Created Bob with ID: {c2_id}")

    # Verify retrieval
    retrieved_c1 = customer_repo.find_by_id(c1_id)
    assert retrieved_c1 is not None
    assert retrieved_c1.name == "Alice Smith"
    print(f"Retrieved Customer: {retrieved_c1.name}, Phone: {retrieved_c1.phone}")

    print("\n--- Testing Transactions ---")
    # Fetch UPI/Online payment mode
    upi_mode = payment_mode_repo.find_by_name("UPI / Online")
    assert upi_mode is not None
    print(f"Using payment mode: {upi_mode.mode_name} (ID: {upi_mode.id})")

    # Alice gets a CREDIT transaction (pays back some money)
    t1 = Transaction(
        id=None,
        customer_id=c1_id,
        transaction_type="CREDIT",
        amount=40.0,
        payment_mode_id=upi_mode.id,
        description="UPI Payment Received"
    )
    # Alice gets a DEBIT transaction (takes goods on credit / gets a charge)
    t2 = Transaction(
        id=None,
        customer_id=c1_id,
        transaction_type="DEBIT",
        amount=150.0,
        payment_mode_id=None,
        description="Bought grocery goods on credit"
    )
    # Alice gets a DAILY_CHARGE
    t3 = Transaction(
        id=None,
        customer_id=c1_id,
        transaction_type="DAILY_CHARGE",
        amount=5.0,
        payment_mode_id=None,
        description="Daily storage fee"
    )

    t1_id = txn_repo.save(t1)
    t2_id = txn_repo.save(t2)
    t3_id = txn_repo.save(t3)
    print(f"Saved transactions with IDs: {t1_id}, {t2_id}, {t3_id}")

    # Verify running balance
    # Alice balance = Opening (100) + Debits (150) + Daily Charges (5) - Credits (40) = 215.0
    alice_balance = customer_repo.get_customer_balance(c1_id)
    print(f"Alice's running balance calculated: {alice_balance}")
    assert alice_balance == 215.0, f"Expected 215.0 but got {alice_balance}"

    print("\n--- Testing Search and Filtering ---")
    all_with_bals = customer_repo.get_all_with_balances(search_query="Alice")
    assert len(all_with_bals) == 1
    print(f"Search results for 'Alice': {all_with_bals[0]['name']} has balance {all_with_bals[0]['current_balance']}")

    debtors = customer_repo.get_all_with_balances(balance_filter="DEBTORS")
    print(f"Debtors (balance > 0): {[d['name'] for d in debtors]}")
    assert len(debtors) == 1, "Only Alice should be a debtor"

    print("\n--- Testing Ledger Joined Query ---")
    ledger_rows = txn_repo.get_ledger_rows(c1_id)
    for row in ledger_rows:
        print(f"Txn ID: {row['id']}, Type: {row['transaction_type']}, Amount: {row['amount']}, Mode: {row['mode_name']}, Desc: '{row['description']}'")

    print("\n--- Testing Foreign Key Cascades & Deletions ---")
    # If we delete Alice, her transactions should be deleted automatically
    delete_result = customer_repo.delete(c1_id)
    assert delete_result is True, "Delete customer should return True"
    
    # Verify transaction count is now 0 for Alice
    c1_txns = txn_repo.find_by_customer(c1_id)
    assert len(c1_txns) == 0, f"Expected 0 transactions for deleted customer but found {len(c1_txns)}"
    print("Checked CASCADE constraints: Alice deleted, all her transactions are cascade-deleted.")

    # Clean up test database
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"Removed test database file {db_file}")

    print("\n*** ALL TESTS PASSED SUCCESSFULLY! ***")

if __name__ == "__main__":
    run_tests()
