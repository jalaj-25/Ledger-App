import customtkinter as ctk
import datetime
import os
from tkinter import filedialog, messagebox
from typing import Optional, List, Dict, Any, Callable
from ledger_app.ui.theme import Theme
from ledger_app.ui.components.data_table import DataTable
from ledger_app.services.customer_service import CustomerService
from ledger_app.services.report_service import ReportService
from ledger_app.services.export_service import ExportService
# pyrefly: ignore [missing-import]
from tkcalendar import Calendar

class CalendarPickerDialog(ctk.CTkToplevel):
    """Popup modal dialog displaying a calendar widget for selecting a date."""
    def __init__(self, parent, initial_date_str: str, on_select: Callable[[str], None]):
        super().__init__(parent)
        self.on_select = on_select
        self.title("Select Date")
        
        # Sizing and centering relative to parent window
        width, height = 320, 360
        parent_top = parent.winfo_toplevel()
        x = parent_top.winfo_x() + (parent_top.winfo_width() - width) // 2
        y = parent_top.winfo_y() + (parent_top.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.resizable(False, False)
        
        # Match Slate theme for visual coherence
        self.configure(fg_color=Theme.BG_SECONDARY)
        self.transient(parent)
        self.grab_set()


        # Set initial selection to today, or parsed value if possible
        default_date = datetime.datetime.now()
        if initial_date_str:
            try:
                # Parse date part
                default_date = datetime.datetime.strptime(initial_date_str.split()[0], "%Y-%m-%d")
            except ValueError:
                pass

        from ledger_app.ui.theme_manager import ThemeManager
        bg_sec = ThemeManager.get_color(Theme.BG_SECONDARY)
        text_prim = ThemeManager.get_color(Theme.TEXT_PRIMARY)
        border_col = ThemeManager.get_color(Theme.BORDER_COLOR)
        bg_sidebar = ThemeManager.get_color(Theme.BG_SIDEBAR)
        text_sec = ThemeManager.get_color(Theme.TEXT_SECONDARY)
        accent_col = ThemeManager.get_color(Theme.ACCENT)
        bg_prim = ThemeManager.get_color(Theme.BG_PRIMARY)
        debit_red = ThemeManager.get_color(Theme.DEBIT_RED)

        # Create Calendar widget
        self.cal = Calendar(
            self,
            selectmode="day",
            year=default_date.year,
            month=default_date.month,
            day=default_date.day,
            background=bg_sec,
            foreground=text_prim,
            bordercolor=border_col,
            headersbackground=bg_sidebar,
            headersforeground=text_sec,
            selectbackground=accent_col,
            selectforeground=bg_prim,
            normalbackground=bg_sec,
            normalforeground=text_prim,
            weekendbackground=bg_prim,
            weekendforeground=debit_red,
            othermonthbackground=bg_prim,
            othermonthforeground=border_col
        )
        self.cal.pack(fill="both", expand=True, padx=15, pady=15)

        # Bottom Actions row
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom", pady=(0, 15), padx=15)

        self.cancel_btn = ctk.CTkButton(
            btn_frame, 
            text="Cancel", 
            fg_color="transparent",
            hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY,
            width=110,
            command=self.destroy
        )
        self.cancel_btn.pack(side="left")

        self.select_btn = ctk.CTkButton(
            btn_frame, 
            text="Select Date", 
            fg_color=Theme.ACCENT,
            hover_color=Theme.ACCENT_HOVER,
            width=110,
            command=self.confirm_selection
        )
        self.select_btn.pack(side="right")

    def confirm_selection(self):
        selected_date = self.cal.selection_get()
        if selected_date:
            formatted_date = selected_date.strftime("%Y-%m-%d")
            self.on_select(formatted_date)
        self.destroy()

class ReportsScreen(ctk.CTkFrame):
    """
    Main View Screen for generating custom analytical reports.
    Provides Date Range filtering, Customer filtering, Outstanding calculations,
    and direct actions to save results as styled PDF or Excel documents.
    """
    def __init__(self, parent, customer_service: CustomerService, 
                 report_service: ReportService, export_service: ExportService):
        super().__init__(parent, fg_color="transparent")

        self.customer_service = customer_service
        self.report_service = report_service
        self.export_service = export_service
        
        self.cust_map = {}       # Map search options to customer IDs
        self.active_headers = [] # Tracks headers of generated report
        self.active_rows = []    # Tracks rows of generated report
        self.report_title = ""   # Title for exporting reports

        # Main Layout configs
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # Table takes up rest space

        # 1. Header Frame Row
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.title_lbl = ctk.CTkLabel(
            self.header_frame, 
            text="Reports & Financial Statements", 
            font=Theme.FONT_TITLE, 
            text_color=Theme.TEXT_PRIMARY,
            anchor="w"
        )
        self.title_lbl.grid(row=0, column=0, sticky="w")

        # 2. Filtering Options Block Panel
        self.filter_card = ctk.CTkFrame(
            self, 
            fg_color=Theme.BG_SECONDARY, 
            corner_radius=Theme.CORNER_RADIUS,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR
        )
        self.filter_card.grid(row=1, column=0, sticky="ew", pady=(0, 20), ipadx=10, ipady=10)
        
        self.filter_card.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.filter_card.grid_rowconfigure((0, 1), weight=1)

        # Field 1: Report Type Selector
        ctk.CTkLabel(self.filter_card, text="Report Type", font=Theme.FONT_BODY_BOLD, anchor="w").grid(row=0, column=0, sticky="w", padx=15, pady=(10, 2))
        self.report_type_menu = ctk.CTkOptionMenu(
            self.filter_card,
            values=["Outstanding Balance Report", "Date Range Transaction Report", "Monthly financial Summary"],
            font=Theme.FONT_BODY,
            corner_radius=Theme.CORNER_RADIUS,
            fg_color=Theme.BG_TERTIARY,
            button_color=Theme.BG_TERTIARY,
            button_hover_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY,
            command=self.on_report_type_change
        )
        self.report_type_menu.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))

        # Field 2: Search Customer Name
        ctk.CTkLabel(self.filter_card, text="Search Customer Name", font=Theme.FONT_BODY_BOLD, anchor="w").grid(row=0, column=1, sticky="w", padx=15, pady=(10, 2))
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self.on_customer_search)
        self.cust_search_entry = ctk.CTkEntry(
            self.filter_card,
            textvariable=self.search_var,
            placeholder_text="Optional: filter by name...",
            font=Theme.FONT_BODY,
            corner_radius=Theme.CORNER_RADIUS
        )
        self.cust_search_entry.grid(row=1, column=1, sticky="ew", padx=15, pady=(0, 10))

        # Customer selection Dropdown (defaults to All Customers)
        self.cust_dropdown = ctk.CTkOptionMenu(
            self.filter_card,
            values=["All Customers"],
            font=Theme.FONT_BODY,
            corner_radius=Theme.CORNER_RADIUS,
            fg_color=Theme.BG_TERTIARY,
            button_color=Theme.BG_TERTIARY,
            button_hover_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY
        )
        # We place this dynamically or enable it. For now, let's span search and selection or keep them side-by-side.
        # Let's grid it on Row 1, Column 1 instead, and move Customer search to Row 0, Column 1.
        # Actually, let's keep search on column 1, and the dropdown selector on column 2:
        ctk.CTkLabel(self.filter_card, text="Selected Customer Filter", font=Theme.FONT_BODY_BOLD, anchor="w").grid(row=0, column=2, sticky="w", padx=15, pady=(10, 2))
        self.cust_dropdown.grid(row=1, column=2, sticky="ew", padx=15, pady=(0, 10))

        # Date pickers
        # Field 3: Date Inputs Frame
        self.dates_label = ctk.CTkLabel(self.filter_card, text="Date Range (Start - End)", font=Theme.FONT_BODY_BOLD, anchor="w")
        self.dates_label.grid(row=0, column=3, sticky="w", padx=15, pady=(10, 2))
        
        self.dates_box = ctk.CTkFrame(self.filter_card, fg_color="transparent")
        self.dates_box.grid(row=1, column=3, sticky="ew", padx=15, pady=(0, 10))
        self.dates_box.columnconfigure(0, weight=4) # Start date field
        self.dates_box.columnconfigure(1, weight=1) # Start calendar button
        self.dates_box.columnconfigure(2, weight=0) # "to" label
        self.dates_box.columnconfigure(3, weight=4) # End date field
        self.dates_box.columnconfigure(4, weight=1) # End calendar button

        self.start_date_entry = ctk.CTkEntry(self.dates_box, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS, placeholder_text="YYYY-MM-DD")
        self.start_date_entry.grid(row=0, column=0, sticky="ew")
        
        self.start_cal_btn = ctk.CTkButton(
            self.dates_box,
            text="📅",
            font=Theme.FONT_BODY,
            width=28,
            fg_color="transparent",
            hover_color=Theme.BG_TERTIARY,
            text_color=Theme.TEXT_PRIMARY,
            command=self.open_start_calendar
        )
        self.start_cal_btn.grid(row=0, column=1, padx=(2, 5))
        
        ctk.CTkLabel(self.dates_box, text="to", font=Theme.FONT_BODY).grid(row=0, column=2, padx=2)
        
        self.end_date_entry = ctk.CTkEntry(self.dates_box, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS, placeholder_text="YYYY-MM-DD")
        self.end_date_entry.grid(row=0, column=3, sticky="ew")

        self.end_cal_btn = ctk.CTkButton(
            self.dates_box,
            text="📅",
            font=Theme.FONT_BODY,
            width=28,
            fg_color="transparent",
            hover_color=Theme.BG_TERTIARY,
            text_color=Theme.TEXT_PRIMARY,
            command=self.open_end_calendar
        )
        self.end_cal_btn.grid(row=0, column=4, padx=(2, 0))

        # Set default dates
        self.set_default_dates()

        # Action Buttons Pane inside filter card
        self.actions_box = ctk.CTkFrame(self.filter_card, fg_color="transparent")
        # Span across all 4 columns at the bottom
        self.actions_box.grid(row=2, column=0, columnspan=4, sticky="ew", padx=15, pady=(10, 0))
        self.actions_box.columnconfigure(0, weight=1)

        self.status_lbl = ctk.CTkLabel(self.actions_box, text="Select parameters and click generate.", font=Theme.FONT_CAPTION, text_color=Theme.TEXT_SECONDARY)
        self.status_lbl.pack(side="left", padx=5)

        self.excel_btn = ctk.CTkButton(
            self.actions_box, text="📊 Export Excel", font=Theme.FONT_BODY_BOLD,
            fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY, state="disabled", command=self.export_excel
        )
        self.excel_btn.pack(side="right", padx=5)

        self.pdf_btn = ctk.CTkButton(
            self.actions_box, text="📄 Export PDF", font=Theme.FONT_BODY_BOLD,
            fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY, state="disabled", command=self.export_pdf
        )
        self.pdf_btn.pack(side="right", padx=5)

        self.generate_btn = ctk.CTkButton(
            self.actions_box, text="Run Report", font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER,
            command=self.run_report
        )
        self.generate_btn.pack(side="right", padx=5)

        # 3. Output Table Grid Container
        self.table_container = ctk.CTkFrame(self, fg_color=Theme.BG_SECONDARY, corner_radius=Theme.CORNER_RADIUS, border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR)
        self.table_container.grid(row=2, column=0, sticky="nsew")
        self.table_container.grid_columnconfigure(0, weight=1)
        self.table_container.grid_rowconfigure(0, weight=1)

        # DataTable widget placeholder (recreated on report runs to resize column weightings)
        self.data_table = None

        # Load dynamic UI bindings
        self.refresh_customer_filters()
        self.on_report_type_change()

    def set_default_dates(self):
        """Prefills date inputs with current month range."""
        today = datetime.datetime.now()
        start_date = datetime.date(today.year, today.month, 1).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
        
        self.start_date_entry.delete(0, "end")
        self.start_date_entry.insert(0, start_date)
        
        self.end_date_entry.delete(0, "end")
        self.end_date_entry.insert(0, end_date)

    def refresh_customer_filters(self, search_text: str = ""):
        """Loads and maps customer filters."""
        try:
            customers = self.customer_service.list_customers(search_text)
            self.cust_map = {c['name']: c['id'] for c in customers}
            
            options = ["All Customers"] + list(self.cust_map.keys())
            self.cust_dropdown.configure(values=options)
            self.cust_dropdown.set("All Customers")
        except Exception as e:
            print(f"Error filtering reports customers list: {e}")

    def on_customer_search(self, *args):
        """Refreshes options list when typing in search field."""
        q = self.search_var.get().strip()
        self.refresh_customer_filters(q)

    def on_report_type_change(self, *args):
        """Disables/enables date selection inputs depending on whether they are relevant."""
        report_type = self.report_type_menu.get()
        
        # Outstanding reports do not need date range inputs
        if "Outstanding" in report_type:
            self.start_date_entry.configure(state="disabled")
            self.end_date_entry.configure(state="disabled")
            self.start_cal_btn.configure(state="disabled")
            self.end_cal_btn.configure(state="disabled")
        else:
            self.start_date_entry.configure(state="normal")
            self.end_date_entry.configure(state="normal")
            self.start_cal_btn.configure(state="normal")
            self.end_cal_btn.configure(state="normal")

    def run_report(self):
        """Gathers criteria, queries ReportService database aggregates, and updates the table."""
        self.status_lbl.configure(text="Running report query...", text_color=Theme.TEXT_SECONDARY)
        
        report_type = self.report_type_menu.get()
        start = self.start_date_entry.get().strip()
        end = self.end_date_entry.get().strip()
        cust_filter = self.cust_dropdown.get()
        customer_id = self.cust_map.get(cust_filter) if cust_filter != "All Customers" else None

        # Clean Table Container first
        if self.data_table:
            self.data_table.destroy()

        # Date validations
        if "Outstanding" not in report_type:
            try:
                # Strictly parse YYYY-MM-DD format (no time allowed)
                start_dt = datetime.datetime.strptime(start, "%Y-%m-%d")
                end_dt = datetime.datetime.strptime(end, "%Y-%m-%d")
                
                # Under the hood, capture full range for transactions (00:00:00 to 23:59:59)
                start = start_dt.strftime("%Y-%m-%d 00:00:00")
                end = end_dt.strftime("%Y-%m-%d 23:59:59")
            except ValueError:
                self.status_lbl.configure(text="Invalid date selection. Please use YYYY-MM-DD format (e.g. 2026-06-13).", text_color=Theme.DEBIT_RED)
                self.pdf_btn.configure(state="disabled")
                self.excel_btn.configure(state="disabled")
                return

        try:
            if "Outstanding" in report_type:
                self.report_title = "Outstanding Balances Statement"
                self.active_headers = ["Customer Name", "Phone No.", "Outstanding Balance"]
                col_weights = [3, 2, 2]
                
                rows = self.report_service.get_outstanding_balances_report()
                self.active_rows = []
                table_data = []
                
                for r in rows:
                    bal = r['current_balance']
                    bal_color = Theme.DEBIT_RED if bal > 0 else Theme.CREDIT_GREEN
                    
                    self.active_rows.append([r['name'], r['phone'] or "-", bal])
                    table_data.append([
                        r['name'],
                        r['phone'] or "-",
                        {"text": f"${bal:,.2f}", "color": bal_color}
                    ])
                
            elif "Date Range" in report_type:
                self.report_title = f"Transactions Statement ({start[:10]} to {end[:10]})"
                self.active_headers = ["Date & Time", "Customer Name", "Type", "Payment Mode", "Description", "Amount"]
                col_weights = [2, 2, 1, 1, 3, 1]
                
                rows = self.report_service.get_date_range_report(start, end)
                
                # Filter by customer ID in memory if requested
                if customer_id is not None:
                    # Find matching name in our service
                    cust_obj = self.customer_service.get_customer_by_id(customer_id)
                    cust_name = cust_obj.name if cust_obj else ""
                    rows = [r for r in rows if r['customer_name'] == cust_name]
                    self.report_title = f"Transactions Statement for {cust_name} ({start[:10]} to {end[:10]})"

                self.active_rows = []
                table_data = []
                
                for r in rows:
                    is_debit = r['transaction_type'] in ("DEBIT", "DAILY_CHARGE")
                    color = Theme.DEBIT_RED if is_debit else Theme.CREDIT_GREEN
                    type_display = "Debit" if r['transaction_type'] == "DEBIT" else ("Charge" if r['transaction_type'] == "DAILY_CHARGE" else "Credit")
                    
                    self.active_rows.append([
                        r['transaction_date'], r['customer_name'], type_display,
                        r['mode_name'] or "-", r['description'] or "-", r['amount']
                    ])
                    table_data.append([
                        r['transaction_date'][:16] if r['transaction_date'] else "-",
                        r['customer_name'],
                        {"text": type_display, "color": color},
                        r['mode_name'] or "-",
                        r['description'] or "-",
                        {"text": f"${r['amount']:,.2f}", "color": color}
                    ])

            else:  # Monthly aggregates
                year = start[:4] if len(start) >= 4 else str(datetime.datetime.now().year)
                self.report_title = f"Monthly summaries for calendar year {year}"
                self.active_headers = ["Month", "Debits (+)", "Charges (+)", "Credits (-)", "Net Owed Change"]
                col_weights = [2, 1, 1, 1, 2]
                
                rows = self.report_service.get_monthly_report(year)
                self.active_rows = []
                table_data = []
                
                for r in rows:
                    net_color = Theme.DEBIT_RED if r['net_change'] > 0 else Theme.CREDIT_GREEN
                    
                    self.active_rows.append([
                        r['month_name'], r['total_debit'], r['total_charges'], r['total_credit'], r['net_change']
                    ])
                    table_data.append([
                        r['month_name'],
                        f"${r['total_debit']:,.2f}",
                        f"${r['total_charges']:,.2f}",
                        f"${r['total_credit']:,.2f}",
                        {"text": f"${r['net_change']:,.2f}", "color": net_color}
                    ])

            # Rebuild table view
            self.data_table = DataTable(self.table_container, self.active_headers, col_weights)
            self.data_table.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
            self.data_table.set_data(table_data)

            # Update status and button locks
            count = len(self.active_rows)
            self.status_lbl.configure(text=f"Report run completed successfully. ({count} entries found)", text_color=Theme.CREDIT_GREEN)
            
            if count > 0:
                self.pdf_btn.configure(state="normal")
                self.excel_btn.configure(state="normal")
            else:
                self.pdf_btn.configure(state="disabled")
                self.excel_btn.configure(state="disabled")

        except Exception as e:
            self.status_lbl.configure(text=f"Database error executing report: {e}", text_color=Theme.DEBIT_RED)
            self.pdf_btn.configure(state="disabled")
            self.excel_btn.configure(state="disabled")

    def export_excel(self):
        """Displays File Save dialog and exports rows to styled Excel spreadsheet."""
        if not self.active_rows:
            return
            
        file_path = filedialog.asksaveasfilename(
            title="Save Excel Statement",
            defaultextension=".xlsx",
            filetypes=[("Excel Worksheets", "*.xlsx")],
            initialfile=self.report_title.replace(" ", "_") + ".xlsx"
        )
        
        if file_path:
            try:
                self.export_service.export_report_to_excel(
                    report_title=self.report_title,
                    headers=self.active_headers,
                    data_rows=self.active_rows,
                    output_path=file_path
                )
                messagebox.showinfo("Export Successful", f"Excel report generated successfully at:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Export Failed", f"An error occurred during Excel export: {e}")

    def export_pdf(self):
        """Displays File Save dialog and exports rows to beautiful PDF document."""
        if not self.active_rows:
            return
            
        file_path = filedialog.asksaveasfilename(
            title="Save PDF Statement",
            defaultextension=".pdf",
            filetypes=[("Portable Document Format", "*.pdf")],
            initialfile=self.report_title.replace(" ", "_") + ".pdf"
        )
        
        if file_path:
            try:
                # Add default branding info
                business_info = {
                    "name": "General Ledger Store",
                    "address": "My Ledger Business Operations Center"
                }
                
                self.export_service.export_report_to_pdf(
                    report_title=self.report_title,
                    headers=self.active_headers,
                    data_rows=self.active_rows,
                    output_path=file_path,
                    business_info=business_info
                )
                messagebox.showinfo("Export Successful", f"PDF report generated successfully at:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Export Failed", f"An error occurred during PDF export: {e}")

    def open_start_calendar(self):
        """Opens the calendar dialog to pick the start date."""
        current_val = self.start_date_entry.get().strip()
        CalendarPickerDialog(self, current_val, on_select=self._set_start_date)

    def _set_start_date(self, date_str: str):
        self.start_date_entry.delete(0, "end")
        self.start_date_entry.insert(0, date_str)

    def open_end_calendar(self):
        """Opens the calendar dialog to pick the end date."""
        current_val = self.end_date_entry.get().strip()
        CalendarPickerDialog(self, current_val, on_select=self._set_end_date)

    def _set_end_date(self, date_str: str):
        self.end_date_entry.delete(0, "end")
        self.end_date_entry.insert(0, date_str)
