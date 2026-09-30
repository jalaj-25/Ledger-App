import customtkinter as ctk
import datetime
from tkinter import messagebox, filedialog
from typing import Callable, Optional
from ledger_app.ui.theme import Theme
from ledger_app.ui.components.stat_card import StatCard
from ledger_app.ui.components.data_table import DataTable
from ledger_app.services.customer_service import CustomerService
from ledger_app.services.ledger_service import LedgerService
from ledger_app.services.transaction_service import TransactionService
from ledger_app.services.export_service import ExportService
from ledger_app.repositories.payment_mode_repository import PaymentModeRepository

class QuickTransactionDialog(ctk.CTkToplevel):
    """Modal popup dialog for quickly logging a transaction on the ledger page."""
    def __init__(self, parent, transaction_service: TransactionService, 
                 payment_mode_repo: PaymentModeRepository, customer_id: int, on_success: Callable):
        super().__init__(parent)
        self.txn_service = transaction_service
        self.mode_repo = payment_mode_repo
        self.customer_id = customer_id
        self.on_success = on_success
        
        self.title("Add Ledger Entry")
        width, height = 400, 420
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.resizable(False, False)
        self.configure(fg_color=Theme.BG_SECONDARY)
        self.transient(parent)
        self.grab_set()

        self.mode_map = {}

        # Title
        ctk.CTkLabel(self, text="Add Ledger Transaction", font=Theme.FONT_SUBTITLE).pack(pady=15)

        # Fields frame
        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=25)
        form.columnconfigure(1, weight=1)

        # 1. Type Segmented Selector
        ctk.CTkLabel(form, text="Entry Type", font=Theme.FONT_BODY_BOLD).grid(row=0, column=0, sticky="w", pady=8)
        self.type_select = ctk.CTkSegmentedButton(
            form, 
            values=["DEBIT (Charge)", "CREDIT (Payment)", "DAILY_CHARGE"],
            font=Theme.FONT_BODY_BOLD,
            selected_color=Theme.ACCENT,
            selected_hover_color=Theme.ACCENT_HOVER,
            command=self.on_type_change
        )
        self.type_select.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=8)
        self.type_select.set("DEBIT (Charge)")

        # 2. Amount
        ctk.CTkLabel(form, text="Amount ($)", font=Theme.FONT_BODY_BOLD).grid(row=1, column=0, sticky="w", pady=8)
        self.amount_entry = ctk.CTkEntry(form, font=Theme.FONT_BODY, placeholder_text="0.00", corner_radius=Theme.CORNER_RADIUS)
        self.amount_entry.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=8)

        # 3. Payment Mode
        ctk.CTkLabel(form, text="Payment Mode", font=Theme.FONT_BODY_BOLD).grid(row=2, column=0, sticky="w", pady=8)
        self.mode_menu = ctk.CTkOptionMenu(
            form, 
            values=["N/A"], 
            font=Theme.FONT_BODY, 
            corner_radius=Theme.CORNER_RADIUS,
            fg_color=Theme.BG_TERTIARY,
            button_color=Theme.BG_TERTIARY,
            text_color=Theme.TEXT_PRIMARY
        )
        self.mode_menu.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=8)

        # 4. Description
        ctk.CTkLabel(form, text="Description", font=Theme.FONT_BODY_BOLD).grid(row=3, column=0, sticky="w", pady=8)
        self.desc_entry = ctk.CTkEntry(form, font=Theme.FONT_BODY, placeholder_text="Notes/Comments", corner_radius=Theme.CORNER_RADIUS)
        self.desc_entry.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=8)

        # Status Error line
        self.error_lbl = ctk.CTkLabel(self, text="", font=Theme.FONT_CAPTION, text_color=Theme.DEBIT_RED)
        self.error_lbl.pack(pady=5)

        # Save Cancel
        btn_box = ctk.CTkFrame(self, fg_color="transparent")
        btn_box.pack(fill="x", side="bottom", pady=20, padx=25)
        
        ctk.CTkButton(
            btn_box, text="Cancel", fg_color="transparent", 
            hover_color=Theme.BG_TERTIARY, border_width=Theme.BORDER_WIDTH, 
            border_color=Theme.BORDER_COLOR, text_color=Theme.TEXT_PRIMARY,
            command=self.destroy
        ).pack(side="left", padx=(0, 10), expand=True, fill="x")

        ctk.CTkButton(
            btn_box, text="Record", fg_color=Theme.ACCENT, 
            hover_color=Theme.ACCENT_HOVER, command=self.save
        ).pack(side="right", expand=True, fill="x")

        self.load_modes()
        self.on_type_change()

    def load_modes(self):
        modes = self.mode_repo.find_all()
        self.mode_map = {m.mode_name: m.id for m in modes}
        options = list(self.mode_map.keys())
        self.mode_menu.configure(values=options)
        if options:
            self.mode_menu.set(options[0])

    def on_type_change(self):
        t = self.type_select.get()
        if "CREDIT" in t:
            self.mode_menu.configure(state="normal")
        else:
            self.mode_menu.configure(state="disabled")
            self.mode_menu.set("N/A")

    def save(self):
        raw_t = self.type_select.get()
        txn_type = "DEBIT"
        if "CREDIT" in raw_t:
            txn_type = "CREDIT"
        elif "DAILY_CHARGE" in raw_t:
            txn_type = "DAILY_CHARGE"

        try:
            amount = float(self.amount_entry.get().strip())
        except ValueError:
            self.error_lbl.configure(text="Please enter a valid numeric amount.")
            return

        pm_id = None
        if txn_type == "CREDIT":
            mode_sel = self.mode_menu.get()
            pm_id = self.mode_map.get(mode_sel)

        desc = self.desc_entry.get().strip() or None
        date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            self.txn_service.record_transaction(
                customer_id=self.customer_id,
                transaction_type=txn_type,
                amount=amount,
                payment_mode_id=pm_id,
                description=desc,
                transaction_date=date_str
            )
            self.on_success()
            self.destroy()
        except ValueError as e:
            self.error_lbl.configure(text=str(e))


class LedgerViewScreen(ctk.CTkFrame):
    """Screen for displaying detailed transaction logs and statements for a specific customer."""
    def __init__(self, parent, customer_service: CustomerService, ledger_service: LedgerService, 
                 transaction_service: TransactionService, payment_mode_repo: PaymentModeRepository,
                 export_service: ExportService, on_back: Callable, analytics_service=None):
        super().__init__(parent, fg_color="transparent")

        self.customer_service = customer_service
        self.ledger_service = ledger_service
        self.transaction_service = transaction_service
        self.payment_mode_repo = payment_mode_repo
        self.export_service = export_service
        self.on_back = on_back
        self.analytics_service = analytics_service
        
        self.customer_id: Optional[int] = None
        self.statement_data: Dict[str, Any] = {}

        # Configure columns weight for layout stretching
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # Table takes up remaining vertical space

        # 1. Header Frame Block (Customer details + back button)
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        self.header_frame.grid_columnconfigure(1, weight=1)

        self.back_btn = ctk.CTkButton(
            self.header_frame, text="← Back to Directory", width=120, font=Theme.FONT_BODY_BOLD,
            fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY, command=self.on_back
        )
        self.back_btn.grid(row=0, column=0, sticky="w", padx=(0, 15))

        self.title_lbl = ctk.CTkLabel(self.header_frame, text="Ledger Statement", font=Theme.FONT_TITLE, text_color=Theme.TEXT_PRIMARY, anchor="w")
        self.title_lbl.grid(row=0, column=1, sticky="w")

        # Dynamic details subheader labels
        self.details_lbl = ctk.CTkLabel(self.header_frame, text="No customer selected.", font=Theme.FONT_BODY, text_color=Theme.TEXT_SECONDARY, anchor="w")
        self.details_lbl.grid(row=1, column=1, sticky="w", pady=(5, 0))

        # 2. KPI row block (Opening Balance, Debits, Credits, Outstanding)
        self.kpi_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.kpi_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        for col in range(4):
            self.kpi_frame.grid_columnconfigure(col, weight=1)

        self.card_open = StatCard(self.kpi_frame, "Opening Balance", "$0.00", Theme.TEXT_PRIMARY)
        self.card_open.grid(row=0, column=0, padx=(0, 5), sticky="nsew")

        self.card_debits = StatCard(self.kpi_frame, "Total Debits (+)", "$0.00", Theme.DEBIT_RED)
        self.card_debits.grid(row=0, column=1, padx=5, sticky="nsew")

        self.card_credits = StatCard(self.kpi_frame, "Total Credits (-)", "$0.00", Theme.CREDIT_GREEN)
        self.card_credits.grid(row=0, column=2, padx=5, sticky="nsew")

        self.card_current = StatCard(self.kpi_frame, "Current Balance", "$0.00", Theme.TEXT_PRIMARY)
        self.card_current.grid(row=0, column=3, padx=(5, 0), sticky="nsew")

        # 3. Tabbed Container Block (Transactions & Customer Analytics)
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
        
        self.tab_view.add("Transactions")
        self.tab_view.add("Analytics")
        
        self.table_container = self.tab_view.tab("Transactions")
        self.table_container.grid_columnconfigure(0, weight=1)
        self.table_container.grid_rowconfigure(1, weight=1)

        # Configure layout for Analytics tab
        tab_analytics = self.tab_view.tab("Analytics")
        tab_analytics.grid_columnconfigure(0, weight=1)
        tab_analytics.grid_rowconfigure(0, weight=1)

        from ledger_app.ui.views.analytics_view import CustomerAnalyticsPanel
        self.analytics_panel = CustomerAnalyticsPanel(tab_analytics, self.analytics_service)
        self.analytics_panel.grid(row=0, column=0, sticky="nsew")

        # Actions Row inside Table Container
        self.actions_box = ctk.CTkFrame(self.table_container, fg_color="transparent")
        self.actions_box.grid(row=0, column=0, sticky="ew", padx=20, pady=12)
        self.actions_box.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.actions_box, text="TRANSACTION LOG", font=Theme.FONT_SUBTITLE).pack(side="left")

        # Action Buttons
        self.excel_btn = ctk.CTkButton(
            self.actions_box, text="📊 Excel Statement", font=Theme.FONT_BODY_BOLD,
            fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY, command=self.export_excel
        )
        self.excel_btn.pack(side="right", padx=5)

        self.pdf_btn = ctk.CTkButton(
            self.actions_box, text="📄 PDF Statement", font=Theme.FONT_BODY_BOLD,
            fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY, command=self.export_pdf
        )
        self.pdf_btn.pack(side="right", padx=5)

        self.add_entry_btn = ctk.CTkButton(
            self.actions_box, text="+ Record Entry", font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER, command=self.open_quick_entry
        )
        self.add_entry_btn.pack(side="right", padx=5)

        # Transaction Table widget
        self.data_table = None

    def load_customer(self, customer_id: int):
        """Loads and binds details for the selected customer ledger."""
        self.customer_id = customer_id
        self.refresh()

    def refresh(self):
        """Queries the latest statement ledger and updates cards and list elements."""
        if not self.customer_id:
            return

        try:
            self.statement_data = self.ledger_service.get_customer_ledger(self.customer_id)
            customer = self.statement_data["customer"]

            # Update Labels
            self.title_lbl.configure(text=f"Ledger: {customer.name}")
            phone_str = f"Phone: {customer.phone}" if customer.phone else "Phone: N/A"
            addr_str = f" | Address: {customer.address}" if customer.address else ""
            self.details_lbl.configure(text=f"{phone_str}{addr_str}")

            # Update KPI Cards
            self.card_open.update_value(f"${self.statement_data['opening_balance']:,.2f}")
            self.card_debits.update_value(f"${self.statement_data['total_debits']:,.2f}", Theme.DEBIT_RED)
            self.card_credits.update_value(f"${self.statement_data['total_credits']:,.2f}", Theme.CREDIT_GREEN)
            
            cur_bal = self.statement_data['current_balance']
            cur_color = Theme.DEBIT_RED if cur_bal > 0 else (Theme.CREDIT_GREEN if cur_bal < 0 else Theme.TEXT_PRIMARY)
            self.card_current.update_value(f"${cur_bal:,.2f}", cur_color)

            # Rebuild Table view
            if self.data_table:
                self.data_table.destroy()

            headers = ["Date & Time", "Description", "Payment Mode", "Debit (+)", "Credit (-)", "Running Bal"]
            weights = [2, 3, 2, 2, 2, 2]
            
            self.data_table = DataTable(self.table_container, headers, weights)
            self.data_table.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")

            table_rows = []
            for txn in self.statement_data["transactions"]:
                is_debit = txn["transaction_type"] in ("DEBIT", "DAILY_CHARGE")
                
                debit_cell = f"${txn['amount']:,.2f}" if is_debit else "-"
                debit_color = Theme.DEBIT_RED if is_debit else Theme.TEXT_PRIMARY
                
                credit_cell = f"${txn['amount']:,.2f}" if not is_debit else "-"
                credit_color = Theme.CREDIT_GREEN if not is_debit else Theme.TEXT_PRIMARY

                bal = txn["running_balance"]
                bal_color = Theme.DEBIT_RED if bal > 0 else (Theme.CREDIT_GREEN if bal < 0 else Theme.TEXT_PRIMARY)

                table_rows.append([
                    txn["transaction_date"][:16] if txn["transaction_date"] else "-",
                    txn["description"] or "-",
                    txn["mode_name"] or "-",
                    {"text": debit_cell, "color": debit_color},
                    {"text": credit_cell, "color": credit_color},
                    {"text": f"${bal:,.2f}", "color": bal_color}
                ])
                
            self.data_table.set_data(table_rows)
            
            # Update customer analytics
            if self.analytics_panel and self.customer_id:
                self.analytics_panel.update_customer_data(self.customer_id)

        except Exception as e:
            if self.analytics_panel:
                self.analytics_panel.clear_charts()
            messagebox.showerror("Error loading statement", f"Failed to compute ledger running balance: {e}")

    def open_quick_entry(self):
        """Launches modal transaction editor popup."""
        if not self.customer_id:
            return
        QuickTransactionDialog(
            self.winfo_toplevel(), 
            self.transaction_service, 
            self.payment_mode_repo, 
            self.customer_id, 
            on_success=self.refresh
        )

    def export_excel(self):
        """Triggers Excel saving dialogues."""
        if not self.statement_data:
            return
        customer = self.statement_data["customer"]
        file_path = filedialog.asksaveasfilename(
            title="Save Excel Ledger",
            defaultextension=".xlsx",
            filetypes=[("Excel Worksheets", "*.xlsx")],
            initialfile=f"Ledger_{customer.name.replace(' ', '_')}.xlsx"
        )
        if file_path:
            try:
                self.export_service.export_ledger_to_excel(self.statement_data, file_path)
                messagebox.showinfo("Export Successful", f"Excel ledger generated at:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Export Failed", f"Excel compilation error: {e}")

    def export_pdf(self):
        """Triggers PDF statement generation."""
        if not self.statement_data:
            return
        customer = self.statement_data["customer"]
        file_path = filedialog.asksaveasfilename(
            title="Save PDF Ledger",
            defaultextension=".pdf",
            filetypes=[("Portable Document Format", "*.pdf")],
            initialfile=f"Ledger_{customer.name.replace(' ', '_')}.pdf"
        )
        if file_path:
            try:
                # Mock branding info
                business_info = {
                    "name": "General Ledger Store",
                    "address": "456 Market Operations Center"
                }
                self.export_service.export_pdf = self.export_service.export_ledger_to_pdf(
                    self.statement_data, file_path, business_info
                )
                messagebox.showinfo("Export Successful", f"PDF statement generated at:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Export Failed", f"PDF compilation error: {e}")
