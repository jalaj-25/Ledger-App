import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from ledger_app.database.db_connection import DatabaseManager
from ledger_app.repositories.customer_repository import CustomerRepository
from ledger_app.repositories.transaction_repository import TransactionRepository
from ledger_app.repositories.payment_mode_repository import PaymentModeRepository

from ledger_app.services.customer_service import CustomerService
from ledger_app.services.transaction_service import TransactionService
from ledger_app.services.ledger_service import LedgerService
from ledger_app.services.report_service import ReportService
from ledger_app.services.export_service import ExportService

def run_service_tests():
    db_file = "test_services.db"
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"Removed old test database {db_file}")

    print("Initializing Database and Repositories...")
    db = DatabaseManager(db_path=db_file)
    c_repo = CustomerRepository(db)
    t_repo = TransactionRepository(db)
    pm_repo = PaymentModeRepository(db)

    print("Initializing Services...")
    customer_service = CustomerService(c_repo)
    transaction_service = TransactionService(t_repo, c_repo, pm_repo)
    ledger_service = LedgerService(c_repo, t_repo)
    report_service = ReportService(db)
    export_service = ExportService()

    print("\n--- Testing Customer Creation ---")
    c1_id = customer_service.create_customer("John Doe", "1234567890", "123 Main St", "Notes test", 100.0)
    c2_id = customer_service.create_customer("Jane Smith", "9876543210", "456 Side St", None, 50.0)
    print(f"Created customer John Doe ID={c1_id}, Jane Smith ID={c2_id}")

    # Test Validation Failure
    try:
        customer_service.create_customer("A", "123")
        assert False, "Should fail validation for short name and invalid phone"
    except ValueError as e:
        print(f"Validation failure caught successfully: {e}")

    print("\n--- Testing Transactions ---")
    upi_id = pm_repo.find_by_name("UPI / Online").id
    cash_id = pm_repo.find_by_name("Cash").id

    # John Doe (ID=1) Debits and Credits
    # Start: 100.0 (opening balance)
    # 1. Debit $150.0 (Grocery)
    # 2. Credit $80.0 (UPI)
    # 3. Daily charge $10.0
    # Current balance should be: 100.0 + 150.0 + 10.0 - 80.0 = 180.0
    t1_id = transaction_service.record_transaction(c1_id, "DEBIT", 150.0, None, "Groceries purchase", "2026-06-01 10:00:00")
    t2_id = transaction_service.record_transaction(c1_id, "CREDIT", 80.0, upi_id, "UPI repayment", "2026-06-02 11:30:00")
    t3_id = transaction_service.record_transaction(c1_id, "DAILY_CHARGE", 10.0, None, "Daily fee", "2026-06-03 09:00:00")
    
    # Jane Smith (ID=2) Credit
    # Start: 50.0
    # 1. Credit $50.0 (Cash)
    # Current balance should be: 50.0 - 50.0 = 0.0
    t4_id = transaction_service.record_transaction(c2_id, "CREDIT", 50.0, cash_id, "Cash payment", "2026-06-02 12:00:00")

    print(f"Recorded transactions: {t1_id}, {t2_id}, {t3_id}, {t4_id}")

    print("\n--- Testing Ledger Balance and Ledger Statement ---")
    john_ledger = ledger_service.get_customer_ledger(c1_id)
    print(f"John Doe Ledger Summary:")
    print(f"  Opening Balance: {john_ledger['opening_balance']}")
    print(f"  Current Balance: {john_ledger['current_balance']}")
    print(f"  Total Debits: {john_ledger['total_debits']}")
    print(f"  Total Credits: {john_ledger['total_credits']}")
    assert john_ledger['current_balance'] == 180.0
    assert len(john_ledger['transactions']) == 3

    print("\n--- Testing Report Service Aggregates ---")
    summary = report_service.get_financial_summary(start_date="2026-06-01", end_date="2026-06-30")
    print(f"Financial summary for June 2026: {summary}")
    # Total debits in transactions: 150.0, total charges: 10.0, total credit: 80 + 50 = 130.0
    # Net outstanding balance change = (150 + 10) - 130 = 30.0
    assert summary['total_debit'] == 150.0
    assert summary['total_charges'] == 10.0
    assert summary['total_credit'] == 130.0
    assert summary['net_change'] == 30.0

    outstanding = report_service.get_outstanding_balances_report()
    print(f"Outstanding non-zero balances: {outstanding}")
    # Only John Doe has non-zero balance (180.0)
    assert len(outstanding) == 1
    assert outstanding[0]['id'] == c1_id

    print("\n--- Testing PDF and Excel Export Engines ---")
    excel_path = "test_john_doe_ledger.xlsx"
    pdf_path = "test_john_doe_ledger.pdf"
    
    if os.path.exists(excel_path):
        os.remove(excel_path)
    if os.path.exists(pdf_path):
        os.remove(pdf_path)

    # Trigger Excel export
    export_service.export_ledger_to_excel(john_ledger, excel_path)
    print(f"Successfully generated Excel ledger at: {excel_path}")
    assert os.path.exists(excel_path), "Excel file was not created!"

    # Trigger PDF export
    business_info = {"name": "Jalajs Ledger Store", "address": "456 Market Road, Dehradun"}
    export_service.export_ledger_to_pdf(john_ledger, pdf_path, business_info)
    print(f"Successfully generated PDF ledger at: {pdf_path}")
    assert os.path.exists(pdf_path), "PDF file was not created!"

    # Clean up test output files
    if os.path.exists(excel_path):
        os.remove(excel_path)
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"Cleaned up test database {db_file}")

    print("\n*** ALL SERVICE LAYER TESTS PASSED SUCCESSFULLY! ***")

if __name__ == "__main__":
    run_service_tests()
