import os
import sys
import customtkinter as ctk

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from ledger_app.database.db_connection import DatabaseManager
from ledger_app.repositories.customer_repository import CustomerRepository
from ledger_app.services.customer_service import CustomerService
from ledger_app.ui.screens.customer_management import CustomerManagementScreen

def test_customer_management_instantiation():
    db_file = "test_cust_mgmt.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    print("Initializing Database, Repositories, and Services...")
    db = DatabaseManager(db_path=db_file)
    c_repo = CustomerRepository(db)
    customer_service = CustomerService(c_repo)

    print("Creating Root Tkinter Window...")
    root = ctk.CTk()
    root.withdraw()

    print("Instantiating CustomerManagementScreen...")
    # Mocking view ledger callback
    def on_view_ledger_callback(customer_id):
        print(f"Callback invoked for customer ID: {customer_id}")

    screen = CustomerManagementScreen(root, customer_service, on_view_ledger_callback)
    
    assert screen is not None
    print("CustomerManagementScreen instantiated successfully!")

    # Clean up
    root.destroy()
    if os.path.exists(db_file):
        os.remove(db_file)

    print("\n*** CUSTOMER MANAGEMENT COMPILATION TEST PASSED! ***")

if __name__ == "__main__":
    test_customer_management_instantiation()
