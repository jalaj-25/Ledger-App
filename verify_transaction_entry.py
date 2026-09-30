import os
import sys
import customtkinter as ctk

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from ledger_app.database.db_connection import DatabaseManager
from ledger_app.repositories.customer_repository import CustomerRepository
from ledger_app.repositories.transaction_repository import TransactionRepository
from ledger_app.repositories.payment_mode_repository import PaymentModeRepository

from ledger_app.services.customer_service import CustomerService
from ledger_app.services.transaction_service import TransactionService
from ledger_app.ui.screens.transaction_entry import TransactionEntryScreen

def test_transaction_entry_instantiation():
    db_file = "test_txn_entry.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    print("Initializing Database, Repositories, and Services...")
    db = DatabaseManager(db_path=db_file)
    c_repo = CustomerRepository(db)
    t_repo = TransactionRepository(db)
    pm_repo = PaymentModeRepository(db)
    
    customer_service = CustomerService(c_repo)
    transaction_service = TransactionService(t_repo, c_repo, pm_repo)

    print("Creating Root Tkinter Window...")
    root = ctk.CTk()
    root.withdraw()

    print("Instantiating TransactionEntryScreen...")
    screen = TransactionEntryScreen(root, customer_service, transaction_service, pm_repo)
    
    assert screen is not None
    print("TransactionEntryScreen instantiated and loaded payment modes successfully!")

    # Clean up
    root.destroy()
    if os.path.exists(db_file):
        os.remove(db_file)

    print("\n*** TRANSACTION ENTRY COMPILATION TEST PASSED! ***")

if __name__ == "__main__":
    test_transaction_entry_instantiation()
