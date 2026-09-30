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
from ledger_app.services.export_service import ExportService
from ledger_app.ui.screens.reports import ReportsScreen

def test_reports_instantiation():
    db_file = "test_reports_screen.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    print("Initializing Database, Repositories, and Services...")
    db = DatabaseManager(db_path=db_file)
    c_repo = CustomerRepository(db)
    t_repo = TransactionRepository(db)
    pm_repo = PaymentModeRepository(db)
    
    customer_service = CustomerService(c_repo)
    report_service = ReportService(db)
    export_service = ExportService()

    print("Creating Root Tkinter Window...")
    root = ctk.CTk()
    root.withdraw()

    print("Instantiating ReportsScreen...")
    screen = ReportsScreen(root, customer_service, report_service, export_service)
    
    assert screen is not None
    print("ReportsScreen instantiated successfully!")

    # Test running a report type to confirm table updates trigger properly
    print("Testing Report Trigger (Outstanding Balance Report)...")
    screen.report_type_menu.set("Outstanding Balance Report")
    screen.on_report_type_change()
    screen.run_report()
    print("Report ran successfully inside widget frame!")

    # Clean up
    root.destroy()
    if os.path.exists(db_file):
        os.remove(db_file)

    print("\n*** REPORTS SCREEN COMPILATION TEST PASSED! ***")

if __name__ == "__main__":
    test_reports_instantiation()
