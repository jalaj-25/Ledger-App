import os
import sys
import customtkinter as ctk

# Ensure workspace is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from ledger_app.database.db_connection import DatabaseManager
from ledger_app.repositories.customer_repository import CustomerRepository
from ledger_app.repositories.transaction_repository import TransactionRepository
from ledger_app.services.customer_service import CustomerService
from ledger_app.services.analytics_service import AnalyticsService

def run_tests():
    db_file = "test_analytics_temp.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    print("=== STARTING ANALYTICS MODULE INTEGRITY TEST ===")
    
    # 1. Init Database and Services
    db = DatabaseManager(db_path=db_file)
    c_repo = CustomerRepository(db)
    t_repo = TransactionRepository(db)
    
    cust_service = CustomerService(c_repo)
    analytics_service = AnalyticsService(db)
    
    # Seed dummy customer & transactions
    print("Seeding test database records...")
    from ledger_app.models.customer import Customer
    cust_id = cust_service.create_customer(
        name="Test Analytics Customer",
        phone="1234567890",
        address="Test Address",
        notes="Notes info",
        opening_balance=1000.0
    )
    
    # Log debit and credit via transactions
    with db.get_connection() as conn:
        conn.execute(
            "INSERT INTO transactions (customer_id, transaction_type, amount, payment_mode_id, description, transaction_date) "
            "VALUES (?, 'DEBIT', 500.0, NULL, 'Test Debit', datetime('now', 'localtime'));",
            (cust_id,)
        )
        conn.execute(
            "INSERT INTO transactions (customer_id, transaction_type, amount, payment_mode_id, description, transaction_date) "
            "VALUES (?, 'CREDIT', 200.0, 1, 'Test Credit via Cash', datetime('now', 'localtime'));",
            (cust_id,)
        )

    # 2. Test Analytics Queries
    print("Testing Analytics Service queries...")
    monthly_data = analytics_service.get_monthly_credit_vs_debit()
    assert len(monthly_data) == 12, f"Expected 12 months, got {len(monthly_data)}"
    print("[PASSED] Monthly Credit vs Debit query")

    top_custs = analytics_service.get_top_customers_by_balance()
    assert len(top_custs) >= 1, "Expected at least 1 top customer"
    assert top_custs[0]["name"] == "Test Analytics Customer"
    print("[PASSED] Top Customers by Balance query")

    rec_pay = analytics_service.get_receivable_vs_payable()
    # Opening balance 1000 + Debit 500 - Credit 200 = 1300 balance (> 0, so receivable)
    assert rec_pay["receivable"] == 1300.0
    assert rec_pay["payable"] == 0.0
    print("[PASSED] Receivable vs Payable query")

    counts = analytics_service.get_monthly_transaction_count()
    assert len(counts) == 12
    # Current month should have 2 transactions
    current_month_count = [x for x in counts if x["count"] > 0]
    assert len(current_month_count) == 1, "Expected current month transactions to show up"
    assert current_month_count[0]["count"] == 2, f"Expected 2 transactions, got {current_month_count[0]['count']}"
    print("[PASSED] Monthly Transaction Count query")

    cust_analytics = analytics_service.get_customer_analytics_data(cust_id)
    assert len(cust_analytics["credit_history"]) == 1
    assert len(cust_analytics["debit_history"]) == 1
    assert len(cust_analytics["running_history"]) == 3 # Opening, Debit, Credit
    assert cust_analytics["running_history"][2]["balance"] == 1300.0
    print("[PASSED] Customer Analytics data compile query")

    # 3. Test View panel instantiation
    print("Testing GUI components instantiation...")
    root = ctk.CTk()
    root.withdraw()

    from ledger_app.ui.views.analytics_view import DashboardAnalyticsPanel, CustomerAnalyticsPanel
    
    dash_panel = DashboardAnalyticsPanel(root, analytics_service)
    dash_panel.update_dashboard_data()
    assert len(dash_panel.canvases) == 6, "Dashboard should render 6 matplotlib canvases"
    print("[PASSED] Dashboard Analytics Panel frame render compile")

    cust_panel = CustomerAnalyticsPanel(root, analytics_service)
    cust_panel.update_customer_data(cust_id)
    assert len(cust_panel.canvases) == 4, "Customer panel should render 4 matplotlib canvases"
    print("[PASSED] Customer Analytics Panel frame render compile")

    # Cleanup GUI and DB
    root.destroy()
    if os.path.exists(db_file):
        os.remove(db_file)

    print("\n*** ALL ANALYTICS INTEGRITY TESTS PASSED SUCCESSFULLY! ***")

if __name__ == "__main__":
    run_tests()
