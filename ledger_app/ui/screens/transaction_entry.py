import customtkinter as ctk
import datetime
from typing import Optional
from ledger_app.ui.theme import Theme
from ledger_app.services.customer_service import CustomerService
from ledger_app.services.transaction_service import TransactionService
from ledger_app.repositories.payment_mode_repository import PaymentModeRepository

class TransactionEntryScreen(ctk.CTkFrame):
    """
    Dedicated view for recording new financial transaction logs (credits, debits, charges)
    with searchable customer autocomplete and date selectors.
    """
    def __init__(self, parent, customer_service: CustomerService, 
                 transaction_service: TransactionService, payment_mode_repo: PaymentModeRepository):
        super().__init__(parent, fg_color="transparent")

        self.customer_service = customer_service
        self.transaction_service = transaction_service
        self.payment_mode_repo = payment_mode_repo
        
        self.cust_map = {}  # Map customer display names to their database IDs
        self.mode_map = {}  # Map mode names to their database IDs

        # Configure columns weights for layout centering
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 1. Header Row
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        self.header_frame.grid_columnconfigure(0, weight=1)
        
        self.title_lbl = ctk.CTkLabel(
            self.header_frame, 
            text="Record Transaction", 
            font=Theme.FONT_TITLE, 
            text_color=Theme.TEXT_PRIMARY,
            anchor="w"
        )
        self.title_lbl.grid(row=0, column=0, sticky="w")

        # 2. Main Form Canvas Frame
        self.form_card = ctk.CTkFrame(
            self, 
            fg_color=Theme.BG_SECONDARY, 
            corner_radius=Theme.CORNER_RADIUS,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR
        )
        self.form_card.grid(row=1, column=0, sticky="n", ipadx=20, ipady=20)
        self.form_card.grid_columnconfigure(1, weight=1)

        # Form Fields Configuration
        # Row 0: Customer Search Input
        ctk.CTkLabel(self.form_card, text="Search Customer Name *", font=Theme.FONT_BODY_BOLD, anchor="w").grid(row=0, column=0, sticky="w", padx=20, pady=(20, 5))
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self.on_search_keypress)
        self.search_entry = ctk.CTkEntry(
            self.form_card, 
            textvariable=self.search_var,
            font=Theme.FONT_BODY, 
            placeholder_text="Start typing to filter list...",
            corner_radius=Theme.CORNER_RADIUS,
            width=300
        )
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=20, pady=(20, 5))

        # Row 1: Selected Customer Dropdown
        ctk.CTkLabel(self.form_card, text="Selected Customer *", font=Theme.FONT_BODY_BOLD, anchor="w").grid(row=1, column=0, sticky="w", padx=20, pady=5)
        self.cust_dropdown = ctk.CTkOptionMenu(
            self.form_card,
            values=["Type in search field first"],
            font=Theme.FONT_BODY,
            corner_radius=Theme.CORNER_RADIUS,
            fg_color=Theme.BG_TERTIARY,
            button_color=Theme.BG_TERTIARY,
            button_hover_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY
        )
        self.cust_dropdown.grid(row=1, column=1, sticky="ew", padx=20, pady=5)

        # Row 2: Transaction Type Segmented Button
        ctk.CTkLabel(self.form_card, text="Transaction Type *", font=Theme.FONT_BODY_BOLD, anchor="w").grid(row=2, column=0, sticky="w", padx=20, pady=10)
        self.type_select = ctk.CTkSegmentedButton(
            self.form_card,
            values=["DEBIT (Charge Owed)", "CREDIT (Payment Recv)", "DAILY_CHARGE (Fee)"],
            font=Theme.FONT_BODY_BOLD,
            corner_radius=Theme.CORNER_RADIUS,
            fg_color=Theme.BG_TERTIARY,
            selected_color=Theme.ACCENT,
            selected_hover_color=Theme.ACCENT_HOVER,
            command=self.on_type_change
        )
        self.type_select.grid(row=2, column=1, sticky="ew", padx=20, pady=10)
        self.type_select.set("DEBIT (Charge Owed)")

        # Row 3: Transaction Amount
        ctk.CTkLabel(self.form_card, text="Amount * ($)", font=Theme.FONT_BODY_BOLD, anchor="w").grid(row=3, column=0, sticky="w", padx=20, pady=10)
        self.amount_entry = ctk.CTkEntry(
            self.form_card, 
            font=Theme.FONT_BODY, 
            placeholder_text="0.00",
            corner_radius=Theme.CORNER_RADIUS
        )
        self.amount_entry.grid(row=3, column=1, sticky="ew", padx=20, pady=10)

        # Row 4: Payment Mode Selection Dropdown
        ctk.CTkLabel(self.form_card, text="Payment Mode", font=Theme.FONT_BODY_BOLD, anchor="w").grid(row=4, column=0, sticky="w", padx=20, pady=10)
        self.mode_dropdown = ctk.CTkOptionMenu(
            self.form_card,
            values=["N/A"],
            font=Theme.FONT_BODY,
            corner_radius=Theme.CORNER_RADIUS,
            fg_color=Theme.BG_TERTIARY,
            button_color=Theme.BG_TERTIARY,
            button_hover_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY
        )
        self.mode_dropdown.grid(row=4, column=1, sticky="ew", padx=20, pady=10)

        # Row 5: Notes/Description
        ctk.CTkLabel(self.form_card, text="Description", font=Theme.FONT_BODY_BOLD, anchor="w").grid(row=5, column=0, sticky="w", padx=20, pady=10)
        self.desc_entry = ctk.CTkEntry(
            self.form_card, 
            font=Theme.FONT_BODY, 
            placeholder_text="Optional description details",
            corner_radius=Theme.CORNER_RADIUS
        )
        self.desc_entry.grid(row=5, column=1, sticky="ew", padx=20, pady=10)

        # Row 6: Transaction Date-Time Picker Selector
        ctk.CTkLabel(self.form_card, text="Date & Time (Local)", font=Theme.FONT_BODY_BOLD, anchor="w").grid(row=6, column=0, sticky="w", padx=20, pady=10)
        
        self.date_frame = ctk.CTkFrame(self.form_card, fg_color="transparent")
        self.date_frame.grid(row=6, column=1, sticky="ew", padx=20, pady=10)
        self.date_frame.columnconfigure(0, weight=1)

        self.date_entry = ctk.CTkEntry(
            self.date_frame, 
            font=Theme.FONT_BODY, 
            placeholder_text="YYYY-MM-DD HH:MM:SS",
            corner_radius=Theme.CORNER_RADIUS
        )
        self.date_entry.grid(row=0, column=0, sticky="ew")
        
        self.now_btn = ctk.CTkButton(
            self.date_frame,
            text="Set to Now",
            width=90,
            font=Theme.FONT_CAPTION,
            fg_color="transparent",
            hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY,
            command=self.set_date_to_now
        )
        self.now_btn.grid(row=0, column=1, padx=(10, 0), sticky="e")

        # Row 7: Action Messages / Save
        self.status_lbl = ctk.CTkLabel(self.form_card, text="", font=Theme.FONT_BODY_BOLD)
        self.status_lbl.grid(row=7, column=0, columnspan=2, pady=(15, 5))

        # Buttons Frame Block
        self.btn_frame = ctk.CTkFrame(self.form_card, fg_color="transparent")
        self.btn_frame.grid(row=8, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="ew")
        self.btn_frame.columnconfigure((0, 1), weight=1)

        self.reset_btn = ctk.CTkButton(
            self.btn_frame, 
            text="Reset Form", 
            fg_color="transparent", 
            hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY,
            command=self.reset_form
        )
        self.reset_btn.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.save_btn = ctk.CTkButton(
            self.btn_frame, 
            text="Record Transaction", 
            fg_color=Theme.ACCENT, 
            hover_color=Theme.ACCENT_HOVER,
            command=self.save_transaction
        )
        self.save_btn.grid(row=0, column=1, padx=(10, 0), sticky="ew")

        # Initialize configurations
        self.load_payment_modes()
        self.refresh_customer_options()
        self.set_date_to_now()
        self.on_type_change()  # Disable payment mode selection initially for DEBIT

    def load_payment_modes(self):
        """Loads payment modes from database and populates options."""
        try:
            modes = self.payment_mode_repo.find_all()
            self.mode_map = {m.mode_name: m.id for m in modes}
            options = list(self.mode_map.keys())
            
            # Select first option or set default
            self.mode_dropdown.configure(values=options)
            if options:
                self.mode_dropdown.set(options[0])
        except Exception as e:
            print(f"Error seeding payment modes: {e}")

    def refresh_customer_options(self, search_text: str = ""):
        """Retrieves and maps customer options based on search query filters."""
        try:
            customers = self.customer_service.list_customers(search_text)
            self.cust_map = {f"{c['name']} (Bal: ${c['current_balance']:,.2f})": c['id'] for c in customers}
            
            options = list(self.cust_map.keys())
            if not options:
                options = ["No matching customer found"]
            
            self.cust_dropdown.configure(values=options)
            self.cust_dropdown.set(options[0])
        except Exception as e:
            print(f"Error fetching customers: {e}")

    def on_search_keypress(self, *args):
        """Triggers dynamic dropdown updates when search inputs are entered."""
        q = self.search_var.get().strip()
        self.refresh_customer_options(q)

    def on_type_change(self, *args):
        """Disables payment mode inputs for charge/debit types, enforces UPI/Cash for credits."""
        selected_type = self.type_select.get()
        if "CREDIT" in selected_type:
            # Enable payment mode dropdown
            self.mode_dropdown.configure(state="normal")
            # Clear disabled style if applicable
        else:
            # Disable payment mode selection since customer is just incurring a charge
            self.mode_dropdown.configure(state="disabled")
            self.mode_dropdown.set("N/A")

    def set_date_to_now(self):
        """Resets target date string entry to local system time."""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.date_entry.delete(0, "end")
        self.date_entry.insert(0, now)

    def reset_form(self):
        """Clears all inputs and restarts values."""
        self.search_entry.delete(0, "end")
        self.amount_entry.delete(0, "end")
        self.desc_entry.delete(0, "end")
        self.set_date_to_now()
        self.type_select.set("DEBIT (Charge Owed)")
        self.on_type_change()
        self.status_lbl.configure(text="")
        self.refresh_customer_options()

    def save_transaction(self):
        """Extracts entries, validates parameters, and logs a database transaction."""
        self.status_lbl.configure(text="")
        
        # 1. Fetch Selected Customer
        cust_selection = self.cust_dropdown.get()
        customer_id = self.cust_map.get(cust_selection)
        if not customer_id:
            self.status_lbl.configure(text="Please search and select a valid customer.", text_color=Theme.DEBIT_RED)
            return

        # 2. Fetch Transaction Type
        raw_type = self.type_select.get()
        txn_type = "DEBIT"
        if "CREDIT" in raw_type:
            txn_type = "CREDIT"
        elif "DAILY_CHARGE" in raw_type:
            txn_type = "DAILY_CHARGE"

        # 3. Parse Amount
        try:
            amount = float(self.amount_entry.get().strip())
        except ValueError:
            self.status_lbl.configure(text="Please enter a valid numeric transaction amount.", text_color=Theme.DEBIT_RED)
            return

        # 4. Fetch Payment Mode
        payment_mode_id = None
        if txn_type == "CREDIT":
            mode_selection = self.mode_dropdown.get()
            payment_mode_id = self.mode_map.get(mode_selection)

        # 5. Description and Date
        desc = self.desc_entry.get().strip() or None
        date_str = self.date_entry.get().strip()
        
        # Simple ISO date validation check
        try:
            datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            self.status_lbl.configure(text="Date format must be YYYY-MM-DD HH:MM:SS", text_color=Theme.DEBIT_RED)
            return

        # Log via service
        try:
            self.transaction_service.record_transaction(
                customer_id=customer_id,
                transaction_type=txn_type,
                amount=amount,
                payment_mode_id=payment_mode_id,
                description=desc,
                transaction_date=date_str
            )
            
            # Show success and reset
            self.status_lbl.configure(text="Transaction recorded successfully!", text_color=Theme.CREDIT_GREEN)
            
            # Reset values but keep customer search criteria to let them log multiple items fast
            self.amount_entry.delete(0, "end")
            self.desc_entry.delete(0, "end")
            self.set_date_to_now()
            
            # Update search options balances
            self.refresh_customer_options(self.search_var.get().strip())
            
        except ValueError as e:
            self.status_lbl.configure(text=str(e), text_color=Theme.DEBIT_RED)
