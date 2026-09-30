import os
import sys
import customtkinter as ctk

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from ledger_app.database.db_connection import DatabaseManager
from ledger_app.repositories.customer_repository import CustomerRepository
from ledger_app.repositories.transaction_repository import TransactionRepository
from ledger_app.repositories.payment_mode_repository import PaymentModeRepository

from ledger_app.services.customer_service import CustomerService
from ledger_app.services.report_service import ReportService
from ledger_app.ui.screens.dashboard import DashboardScreen

def test_dashboard_instantiation():
    db_file = "test_dashboard.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    print("Initializing Database, Repositories, and Services...")
    db = DatabaseManager(db_path=db_file)
    c_repo = CustomerRepository(db)
    t_repo = TransactionRepository(db)
    pm_repo = PaymentModeRepository(db)
    
    customer_service = CustomerService(c_repo)
    report_service = ReportService(db)

    print("Creating Root Tkinter Window...")
    root = ctk.CTk()
    root.withdraw()  # Hide the main window to avoid popping it up on user screen

    print("Instantiating DashboardScreen...")
    # This will compile all frames, widgets, DataTable and execute the initial refresh()
    dashboard = DashboardScreen(root, customer_service, report_service, None)
    
    assert dashboard is not None
    print("DashboardScreen instantiated and refreshed successfully!")

    # Clean up
    root.destroy()
    if os.path.exists(db_file):
        os.remove(db_file)

    print("\n*** DASHBOARD COMPILATION TEST PASSED! ***")

if __name__ == "__main__":
    test_dashboard_instantiation()
