import customtkinter as ctk
from ledger_app.ui.theme import Theme
from ledger_app.ui.components.stat_card import StatCard
from ledger_app.ui.components.data_table import DataTable
from ledger_app.services.customer_service import CustomerService
from ledger_app.services.report_service import ReportService

class DashboardScreen(ctk.CTkFrame):
    """
    Main Analytics Dashboard Screen containing key financial metrics (KPIs)
    and a table displaying recent transactions.
    """
    def __init__(self, parent, customer_service: CustomerService, report_service: ReportService, analytics_service=None):
        super().__init__(parent, fg_color="transparent")
        
        self.customer_service = customer_service
        self.report_service = report_service
        self.analytics_service = analytics_service
        
        # Configure layout weights for responsive stretching
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # Recent transactions table takes rest space

        # 1. Header Block
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        self.header_frame.grid_columnconfigure(0, weight=1)
        
        self.title_lbl = ctk.CTkLabel(
            self.header_frame, 
            text="Financial Dashboard", 
            font=Theme.FONT_TITLE, 
            text_color=Theme.TEXT_PRIMARY,
            anchor="w"
        )
        self.title_lbl.grid(row=0, column=0, sticky="w")
        
        self.refresh_btn = ctk.CTkButton(
            self.header_frame,
            text="Refresh Data",
            font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.ACCENT,
            hover_color=Theme.ACCENT_HOVER,
            corner_radius=Theme.CORNER_RADIUS,
            width=120,
            command=self.refresh
        )
        self.refresh_btn.grid(row=0, column=1, sticky="e")

        # 2. KPI Cards Grid Row
        self.kpi_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.kpi_frame.grid(row=1, column=0, sticky="ew", pady=(0, 25))
        
        # Make the columns in the KPI frame stretch equally
        for col in range(4):
            self.kpi_frame.grid_columnconfigure(col, weight=1)
            
        # Instantiate cards
        self.cust_card = StatCard(self.kpi_frame, "Total Customers", "0", Theme.NEUTRAL_BLUE, "👤")
        self.cust_card.grid(row=0, column=0, padx=(0, 10), sticky="nsew")

        self.debit_card = StatCard(self.kpi_frame, "Total Debit (Owed)", "$0.00", Theme.DEBIT_RED, "📈")
        self.debit_card.grid(row=0, column=1, padx=5, sticky="nsew")

        self.credit_card = StatCard(self.kpi_frame, "Total Credit (Paid)", "$0.00", Theme.CREDIT_GREEN, "📉")
        self.credit_card.grid(row=0, column=2, padx=5, sticky="nsew")

        self.outstanding_card = StatCard(self.kpi_frame, "Net Outstanding", "$0.00", Theme.TEXT_PRIMARY, "💰")
        self.outstanding_card.grid(row=0, column=3, padx=(10, 0), sticky="nsew")

        # 3. Tabbed Container Block (Recent Transactions & Dashboard Analytics)
        self.tab_view = ctk.CTkTabview(
            self,
            fg_color=Theme.BG_SECONDARY,
            segmented_button_selected_color=Theme.ACCENT,
            segmented_button_selected_hover_color=Theme.ACCENT_HOVER,
            segmented_button_unselected_color=Theme.BG_TERTIARY,
            text_color=Theme.TEXT_PRIMARY,
            corner_radius=Theme.CORNER_RADIUS
        )
        self.tab_view.grid(row=2, column=0, sticky="nsew")
        
        self.tab_view.add("Recent Transactions")
        self.tab_view.add("Financial Analytics")

        # Configure layout for Recent Transactions tab
        tab_txns = self.tab_view.tab("Recent Transactions")
        tab_txns.grid_columnconfigure(0, weight=1)
        tab_txns.grid_rowconfigure(1, weight=1)

        self.section_title = ctk.CTkLabel(
            tab_txns,
            text="RECENT TRANSACTIONS",
            font=Theme.FONT_SUBTITLE,
            text_color=Theme.TEXT_PRIMARY,
            anchor="w"
        )
        self.section_title.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")

        # Setup Table
        headers = ["Date & Time", "Customer", "Type", "Payment Mode", "Amount"]
        weights = [2, 2, 1, 1, 1]  # Col weight sizing ratio
        self.recent_table = DataTable(tab_txns, headers, weights)
        self.recent_table.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")

        # Configure layout for Financial Analytics tab
        tab_analytics = self.tab_view.tab("Financial Analytics")
        tab_analytics.grid_columnconfigure(0, weight=1)
        tab_analytics.grid_rowconfigure(0, weight=1)

        from ledger_app.ui.views.analytics_view import DashboardAnalyticsPanel
        self.analytics_panel = DashboardAnalyticsPanel(tab_analytics, self.analytics_service)
        self.analytics_panel.grid(row=0, column=0, sticky="nsew")

        # Load initial values
        self.refresh()

    def refresh(self):
        """Fetches the latest database metrics and updates the dashboard view."""
        try:
            summary = self.report_service.get_financial_summary()
            customers = self.customer_service.list_customers()
            
            # Retrieve last 10 transactions across the system
            recent_txns = self.report_service.get_date_range_report(
                start_date="1970-01-01 00:00:00", 
                end_date="2099-12-31 23:59:59"
            )[:10]

            # 1. Update KPI numbers
            self.cust_card.update_value(str(len(customers)))
            
            if self.analytics_service:
                rec_pay = self.analytics_service.get_receivable_vs_payable()
                total_debit_charges = rec_pay["receivable"]
                total_credit_val = rec_pay["payable"]
                net_outstanding = total_debit_charges - total_credit_val
            else:
                total_debit_charges = summary['total_debit'] + summary['total_charges']
                total_credit_val = summary['total_credit']
                net_outstanding = summary['net_change']

            self.debit_card.update_value(f"${total_debit_charges:,.2f}", Theme.DEBIT_RED)
            self.credit_card.update_value(f"${total_credit_val:,.2f}", Theme.CREDIT_GREEN)
            
            if net_outstanding > 0:
                outstanding_color = Theme.DEBIT_RED
            elif net_outstanding < 0:
                outstanding_color = Theme.CREDIT_GREEN
            else:
                outstanding_color = Theme.TEXT_PRIMARY
            self.outstanding_card.update_value(f"${net_outstanding:,.2f}", outstanding_color)

            # 2. Update recent transaction grid
            table_rows = []
            for txn in recent_txns:
                txn_type = txn['transaction_type']
                is_debit = txn_type in ('DEBIT', 'DAILY_CHARGE')
                
                type_color = Theme.DEBIT_RED if is_debit else Theme.CREDIT_GREEN
                type_display = "Debit" if txn_type == "DEBIT" else ("Charge" if txn_type == "DAILY_CHARGE" else "Credit")
                
                table_rows.append([
                    txn['transaction_date'][:16] if txn['transaction_date'] else "-",
                    txn['customer_name'],
                    {"text": type_display, "color": type_color},
                    txn['mode_name'] or "-",
                    {"text": f"${txn['amount']:,.2f}", "color": type_color}
                ])
                
            self.recent_table.set_data(table_rows)
            
            # Refresh Analytics
            if self.analytics_panel:
                self.analytics_panel.update_dashboard_data()
            
        except Exception as e:
            # Handle empty/uninitialized DB values gracefully
            print(f"Error loading dashboard: {e}")
            self.cust_card.update_value("0")
            self.debit_card.update_value("$0.00", Theme.DEBIT_RED)
            self.credit_card.update_value("$0.00", Theme.CREDIT_GREEN)
            self.outstanding_card.update_value("$0.00", Theme.TEXT_PRIMARY)
            self.recent_table.clear()
            self.recent_table.set_data([])
            if self.analytics_panel:
                self.analytics_panel.clear_charts()
