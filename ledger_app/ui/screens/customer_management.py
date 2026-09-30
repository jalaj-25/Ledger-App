import customtkinter as ctk
from tkinter import messagebox
from typing import Optional, Callable
from ledger_app.ui.theme import Theme
from ledger_app.services.customer_service import CustomerService
from ledger_app.models.customer import BUILTIN_TAGS

# ── Tag visual configuration ────────────────────────────────────────────────────
TAG_COLORS = {
    "General":   ("#64748B", "#94A3B8"),   # slate  (light, dark)
    "Retail":    ("#0EA5E9", "#38BDF8"),   # sky blue
    "Wholesale": ("#8B5CF6", "#A78BFA"),   # violet
    "VIP":       ("#F59E0B", "#FCD34D"),   # amber
    "Supplier":  ("#22C55E", "#4ADE80"),   # green
    "Family":    ("#EC4899", "#F472B6"),   # pink
}
TAG_BG_COLORS = {
    "General":   ("#F1F5F9", "#1E293B"),
    "Retail":    ("#E0F2FE", "#0C4A6E"),
    "Wholesale": ("#EDE9FE", "#2E1065"),
    "VIP":       ("#FEF3C7", "#451A03"),
    "Supplier":  ("#DCFCE7", "#14532D"),
    "Family":    ("#FCE7F3", "#500724"),
}

def _get_tag_color(tag: str) -> str:
    """Returns the accent hex color for the given tag label."""
    return TAG_COLORS.get(tag, TAG_COLORS["General"])[1]   # always use dark-mode colour for badges

def _get_tag_bg(tag: str) -> str:
    return TAG_BG_COLORS.get(tag, TAG_BG_COLORS["General"])[1]


class CustomerFormDialog(ctk.CTkToplevel):
    """Modal dialog for adding or editing customer details."""
    def __init__(self, parent, customer_service: CustomerService,
                 customer_id: Optional[int] = None, on_success: Optional[Callable] = None):
        super().__init__(parent)
        
        self.customer_service = customer_service
        self.customer_id = customer_id
        self.on_success = on_success
        
        is_edit = customer_id is not None
        self.title("Edit Customer" if is_edit else "Add New Customer")
        
        # Geometry and positioning (center on parent screen window)
        width, height = 450, 560
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Configure window styles
        self.resizable(False, False)
        self.configure(fg_color=Theme.BG_SECONDARY)
        self.transient(parent)
        self.grab_set()  # Make window modal

        # Title Label
        title_lbl = ctk.CTkLabel(
            self,
            text="Edit Customer details" if is_edit else "Add New Customer",
            font=Theme.FONT_SUBTITLE,
            text_color=Theme.TEXT_PRIMARY
        )
        title_lbl.pack(pady=(20, 15))

        # Fields container
        fields_frame = ctk.CTkFrame(self, fg_color="transparent")
        fields_frame.pack(fill="both", expand=True, padx=30)
        fields_frame.columnconfigure(1, weight=1)

        # 1. Name
        ctk.CTkLabel(fields_frame, text="Name *", font=Theme.FONT_BODY_BOLD).grid(row=0, column=0, sticky="w", pady=10)
        self.name_entry = ctk.CTkEntry(fields_frame, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS)
        self.name_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=10)

        # 2. Phone
        ctk.CTkLabel(fields_frame, text="Phone", font=Theme.FONT_BODY_BOLD).grid(row=1, column=0, sticky="w", pady=10)
        self.phone_entry = ctk.CTkEntry(fields_frame, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS, placeholder_text="e.g. 10 digits")
        self.phone_entry.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=10)

        # 3. Address
        ctk.CTkLabel(fields_frame, text="Address", font=Theme.FONT_BODY_BOLD).grid(row=2, column=0, sticky="w", pady=10)
        self.address_entry = ctk.CTkEntry(fields_frame, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS)
        self.address_entry.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=10)

        # 4. Opening Balance
        ctk.CTkLabel(fields_frame, text="Op. Balance", font=Theme.FONT_BODY_BOLD).grid(row=3, column=0, sticky="w", pady=10)
        self.balance_entry = ctk.CTkEntry(fields_frame, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS)
        self.balance_entry.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=10)
        self.balance_entry.insert(0, "0.0")
        
        # Disallow editing opening balance if updating to protect ledger balance calculation audit trace
        if is_edit:
            self.balance_entry.configure(state="disabled")

        # 5. Customer Tag
        ctk.CTkLabel(fields_frame, text="Category Tag", font=Theme.FONT_BODY_BOLD).grid(row=4, column=0, sticky="w", pady=10)

        # Tag dropdown — built-in tags + "Custom…" option
        self._tag_options = BUILTIN_TAGS + ["Custom…"]
        self.tag_var = ctk.StringVar(value="General")
        self.tag_menu = ctk.CTkOptionMenu(
            fields_frame,
            values=self._tag_options,
            variable=self.tag_var,
            font=Theme.FONT_BODY,
            corner_radius=Theme.CORNER_RADIUS,
            fg_color=Theme.BG_TERTIARY,
            button_color=Theme.BG_TERTIARY,
            button_hover_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY,
            command=self._on_tag_changed
        )
        self.tag_menu.grid(row=4, column=1, sticky="ew", padx=(10, 0), pady=10)

        # Custom tag entry — revealed only when "Custom…" is selected
        self.custom_tag_entry = ctk.CTkEntry(
            fields_frame, font=Theme.FONT_BODY,
            corner_radius=Theme.CORNER_RADIUS,
            placeholder_text="Enter custom tag name…"
        )
        self.custom_tag_entry.grid(row=5, column=1, sticky="ew", padx=(10, 0), pady=(0, 10))
        self.custom_tag_entry.grid_remove()  # hidden by default

        # 6. Notes
        ctk.CTkLabel(fields_frame, text="Notes", font=Theme.FONT_BODY_BOLD).grid(row=6, column=0, sticky="nw", pady=10)
        self.notes_entry = ctk.CTkTextbox(fields_frame, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS, height=70)
        self.notes_entry.grid(row=6, column=1, sticky="ew", padx=(10, 0), pady=10)

        # Error label
        self.error_lbl = ctk.CTkLabel(self, text="", font=Theme.FONT_CAPTION, text_color=Theme.DEBIT_RED)
        self.error_lbl.pack(pady=5)

        # Bottom Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom", pady=20, padx=30)
        
        self.cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            fg_color="transparent",
            hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY,
            command=self.destroy
        )
        self.cancel_btn.pack(side="left", padx=(0, 10), expand=True, fill="x")

        self.save_btn = ctk.CTkButton(
            btn_frame,
            text="Save Details",
            fg_color=Theme.ACCENT,
            hover_color=Theme.ACCENT_HOVER,
            command=self.save
        )
        self.save_btn.pack(side="right", expand=True, fill="x")

        if is_edit:
            self.load_customer_data()

    def _on_tag_changed(self, value: str):
        """Show or hide the custom tag entry depending on dropdown selection."""
        if value == "Custom…":
            self.custom_tag_entry.grid()
            self.custom_tag_entry.focus()
        else:
            self.custom_tag_entry.grid_remove()
            self.custom_tag_entry.delete(0, "end")

    def _get_selected_tag(self) -> str:
        """Returns the effective tag — either the dropdown selection or custom input."""
        sel = self.tag_var.get()
        if sel == "Custom…":
            custom = self.custom_tag_entry.get().strip()
            return custom if custom else "General"
        return sel

    def load_customer_data(self):
        """Pre-populates fields during edit mode."""
        customer = self.customer_service.get_customer_by_id(self.customer_id)
        if customer:
            self.name_entry.insert(0, customer.name)
            if customer.phone:
                self.phone_entry.insert(0, customer.phone)
            if customer.address:
                self.address_entry.insert(0, customer.address)
            
            # Opening balance loading (temporarily enabled to insert)
            self.balance_entry.configure(state="normal")
            self.balance_entry.delete(0, "end")
            self.balance_entry.insert(0, str(customer.opening_balance))
            self.balance_entry.configure(state="disabled")
            
            # Tag loading — handle custom tags not in the built-in list
            tag = customer.customer_tag or "General"
            if tag in BUILTIN_TAGS:
                self.tag_var.set(tag)
            else:
                self.tag_var.set("Custom…")
                self.custom_tag_entry.grid()
                self.custom_tag_entry.insert(0, tag)

            if customer.notes:
                self.notes_entry.insert("1.0", customer.notes)

    def save(self):
        """Triggers service saving operations."""
        name = self.name_entry.get().strip()
        phone = self.phone_entry.get().strip() or None
        address = self.address_entry.get().strip() or None
        notes = self.notes_entry.get("1.0", "end-1c").strip() or None
        tag = self._get_selected_tag()
        
        try:
            balance = float(self.balance_entry.get().strip() or "0.0")
        except ValueError:
            self.error_lbl.configure(text="Opening balance must be a decimal number.")
            return

        try:
            if self.customer_id:
                self.customer_service.update_customer(
                    self.customer_id, name, phone, address, notes, balance, tag
                )
            else:
                self.customer_service.create_customer(
                    name, phone, address, notes, balance, tag
                )
            
            if self.on_success:
                self.on_success()
            self.destroy()
        except ValueError as e:
            self.error_lbl.configure(text=str(e))


# ── Tag Badge helper widget ─────────────────────────────────────────────────────

class TagBadge(ctk.CTkLabel):
    """Compact coloured pill label displaying the customer's category tag."""
    def __init__(self, parent, tag: str, **kwargs):
        tag_color = _get_tag_color(tag)
        tag_bg    = _get_tag_bg(tag)
        super().__init__(
            parent,
            text=f" {tag} ",
            font=(Theme.FONT_FAMILY, 9, "bold"),
            text_color=tag_color,
            fg_color=tag_bg,
            corner_radius=6,
            **kwargs
        )


# ── Main Customer Management Screen ────────────────────────────────────────────

class CustomerManagementScreen(ctk.CTkFrame):
    """Main View Screen for Customer listing, searching, editing, and deletion operations."""
    def __init__(self, parent, customer_service: CustomerService,
                 on_view_ledger: Callable[[int], None],
                 transaction_service=None,
                 payment_mode_repo=None,
                 backup_manager=None):
        super().__init__(parent, fg_color="transparent")
        
        self.customer_service    = customer_service
        self.on_view_ledger      = on_view_ledger
        self.transaction_service = transaction_service
        self.payment_mode_repo   = payment_mode_repo
        self.backup_manager      = backup_manager
        self._active_tag_filter  = "All"   # tracks currently selected tag pill

        # Main Grid Layout Config
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)  # List container takes available room

        # ── 1. Header Frame Row ──────────────────────────────────────────────
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.title_lbl = ctk.CTkLabel(
            self.header_frame,
            text="Customer Directory",
            font=Theme.FONT_TITLE,
            text_color=Theme.TEXT_PRIMARY,
            anchor="w"
        )
        self.title_lbl.grid(row=0, column=0, sticky="w")

        self.add_btn = ctk.CTkButton(
            self.header_frame,
            text="+ Add Customer",
            font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.ACCENT,
            hover_color=Theme.ACCENT_HOVER,
            corner_radius=Theme.CORNER_RADIUS,
            command=self.open_add_dialog
        )
        self.add_btn.grid(row=0, column=1, sticky="e", padx=(0, 8))

        self.import_btn = ctk.CTkButton(
            self.header_frame,
            text="📥  Import Excel",
            font=Theme.FONT_BODY_BOLD,
            fg_color="transparent",
            hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.ACCENT,
            text_color=Theme.ACCENT,
            corner_radius=Theme.CORNER_RADIUS,
            command=self.open_import_wizard
        )
        self.import_btn.grid(row=0, column=2, sticky="e")

        # ── 2. Tag Filter Pill Bar ───────────────────────────────────────────
        self.tag_bar_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.tag_bar_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self._tag_pill_btns: dict[str, ctk.CTkButton] = {}
        self._build_tag_bar()

        # ── 3. Search & Balance Filter Bar ──────────────────────────────────
        self.filter_frame = ctk.CTkFrame(
            self,
            fg_color=Theme.BG_SECONDARY,
            corner_radius=Theme.CORNER_RADIUS,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR
        )
        self.filter_frame.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        self.filter_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            self.filter_frame,
            placeholder_text="Search customer by Name or Phone...",
            font=Theme.FONT_BODY,
            corner_radius=Theme.CORNER_RADIUS
        )
        self.search_entry.grid(row=0, column=0, padx=15, pady=12, sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_list())

        self.type_filter = ctk.CTkOptionMenu(
            self.filter_frame,
            values=["All Customers", "Debtors (Owe money)", "Creditors (In Credit)"],
            font=Theme.FONT_BODY,
            corner_radius=Theme.CORNER_RADIUS,
            fg_color=Theme.BG_TERTIARY,
            button_color=Theme.BG_TERTIARY,
            button_hover_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY,
            command=lambda val: self.refresh_list()
        )
        self.type_filter.grid(row=0, column=1, padx=(0, 15), pady=12, sticky="e")

        # ── 4. Main Data Scrollable List ─────────────────────────────────────
        self.list_section = ctk.CTkFrame(
            self,
            fg_color=Theme.BG_SECONDARY,
            corner_radius=Theme.CORNER_RADIUS,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR
        )
        self.list_section.grid(row=3, column=0, sticky="nsew")
        self.list_section.grid_columnconfigure(0, weight=1)
        self.list_section.grid_rowconfigure(1, weight=1)

        # Grid header columns
        self.list_header = ctk.CTkFrame(self.list_section, fg_color=Theme.BG_TERTIARY, height=35, corner_radius=0)
        self.list_header.grid(row=0, column=0, sticky="ew")
        self.list_header.grid_columnconfigure(0, weight=3)  # Name + tag
        self.list_header.grid_columnconfigure(1, weight=2)  # Phone
        self.list_header.grid_columnconfigure(2, weight=2)  # Balance
        self.list_header.grid_columnconfigure(3, weight=3)  # Actions

        headers = [
            ("Name", 0, "w"),
            ("Phone", 1, "center"),
            ("Balance", 2, "e"),
            ("Actions", 3, "center")
        ]
        for text, col, align in headers:
            lbl = ctk.CTkLabel(
                self.list_header,
                text=text.upper(),
                font=Theme.FONT_HEADER,
                text_color=Theme.TEXT_PRIMARY,
                anchor=align,
                pady=8
            )
            lbl.grid(row=0, column=col, sticky="nsew", padx=20)

        self.scroll_frame = ctk.CTkScrollableFrame(self.list_section, fg_color="transparent", corner_radius=0)
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=1, pady=1)
        self.scroll_frame.grid_columnconfigure(0, weight=3)
        self.scroll_frame.grid_columnconfigure(1, weight=2)
        self.scroll_frame.grid_columnconfigure(2, weight=2)
        self.scroll_frame.grid_columnconfigure(3, weight=3)

        # Initial list refresh
        self.refresh_list()

    # ── Tag Pill Bar ──────────────────────────────────────────────────────────

    def _build_tag_bar(self):
        """Creates the horizontal row of tag filter pills."""
        for w in self.tag_bar_frame.winfo_children():
            w.destroy()
        self._tag_pill_btns.clear()

        # Build tag options dynamically:
        #   1. Start with built-in tags (always shown)
        #   2. Append any custom tags that exist in the DB but aren't built-in
        try:
            db_tag_counts = self.customer_service.get_customer_counts_by_tag()
            custom_tags = [t for t in db_tag_counts if t not in BUILTIN_TAGS]
        except Exception:
            custom_tags = []

        tag_options = ["All"] + BUILTIN_TAGS + custom_tags


        ctk.CTkLabel(
            self.tag_bar_frame,
            text="Filter by Tag:",
            font=Theme.FONT_BODY_BOLD,
            text_color=Theme.TEXT_SECONDARY
        ).pack(side="left", padx=(0, 8))

        for tag in tag_options:
            is_active = (tag == self._active_tag_filter)
            tag_color = _get_tag_color(tag) if tag != "All" else Theme.ACCENT
            btn = ctk.CTkButton(
                self.tag_bar_frame,
                text=tag,
                font=Theme.FONT_CAPTION,
                width=70, height=26,
                corner_radius=13,
                fg_color=tag_color if is_active else "transparent",
                hover_color=_get_tag_bg(tag) if tag != "All" else Theme.BG_TERTIARY,
                border_width=1,
                border_color=tag_color if tag != "All" else Theme.ACCENT,
                text_color=Theme.TEXT_WHITE if is_active else (tag_color if tag != "All" else Theme.ACCENT),
                command=lambda t=tag: self._select_tag_filter(t)
            )
            btn.pack(side="left", padx=3)
            self._tag_pill_btns[tag] = btn

    def _select_tag_filter(self, tag: str):
        """Updates active tag filter and refreshes the list."""
        self._active_tag_filter = tag
        self._build_tag_bar()   # re-render pills with updated active state
        self.refresh_list()

    # ── List Refresh ──────────────────────────────────────────────────────────

    def refresh_list(self):
        """Queries the customer directory and populates the scroll layout list."""
        # Rebuild tag pills first — picks up any newly created custom tags
        self._build_tag_bar()

        for w in self.scroll_frame.winfo_children():
            w.destroy()

        search_q   = self.search_entry.get().strip()
        filter_val = self.type_filter.get()

        # Map filter text to service codes
        filter_code = None
        if "Debtors" in filter_val:
            filter_code = "DEBTORS"
        elif "Creditors" in filter_val:
            filter_code = "CREDITORS"

        # Active tag filter (None means All)
        tag_filter = None if self._active_tag_filter == "All" else self._active_tag_filter

        customers = self.customer_service.list_customers(search_q, filter_code, tag_filter)

        for idx, cust in enumerate(customers):
            bg_color = Theme.BG_SECONDARY if idx % 2 == 0 else Theme.BG_PRIMARY
            row_id   = cust['id']
            tag      = cust.get('customer_tag', 'General') or 'General'

            for col_idx in range(4):
                cell_bg = ctk.CTkFrame(self.scroll_frame, fg_color=bg_color, corner_radius=0)
                cell_bg.grid(row=idx, column=col_idx, sticky="nsew", ipady=8)

                if col_idx == 0:  # Name + Tag badge
                    cell_bg.grid_columnconfigure(0, weight=1)
                    name_row = ctk.CTkFrame(cell_bg, fg_color="transparent")
                    name_row.grid(row=0, column=0, sticky="ew", padx=12, pady=4)

                    lbl = ctk.CTkLabel(
                        name_row, text=cust['name'],
                        font=Theme.FONT_BODY_BOLD, text_color=Theme.TEXT_PRIMARY, anchor="w"
                    )
                    lbl.pack(side="left")

                    # Tag badge pill
                    badge = TagBadge(name_row, tag)
                    badge.pack(side="left", padx=(6, 0))

                elif col_idx == 1:  # Phone
                    cell_bg.grid_columnconfigure(0, weight=1)
                    lbl = ctk.CTkLabel(
                        cell_bg, text=cust['phone'] or "-",
                        font=Theme.FONT_BODY, text_color=Theme.TEXT_SECONDARY
                    )
                    lbl.grid(row=0, column=0, padx=10, pady=4)

                elif col_idx == 2:  # Balance
                    cell_bg.grid_columnconfigure(0, weight=1)
                    bal = cust['current_balance']
                    bal_color = Theme.DEBIT_RED if bal > 0 else (Theme.CREDIT_GREEN if bal < 0 else Theme.TEXT_PRIMARY)
                    lbl = ctk.CTkLabel(
                        cell_bg, text=f"₹{bal:,.2f}",
                        font=Theme.FONT_BODY_BOLD, text_color=bal_color, anchor="e"
                    )
                    lbl.grid(row=0, column=0, sticky="ew", padx=20, pady=4)

                elif col_idx == 3:  # Actions
                    btn_box = ctk.CTkFrame(cell_bg, fg_color="transparent")
                    btn_box.pack(anchor="center")

                    btn_ledg = ctk.CTkButton(
                        btn_box, text="Ledger", width=65, height=24, font=Theme.FONT_CAPTION,
                        fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER,
                        command=lambda cid=row_id: self.on_view_ledger(cid)
                    )
                    btn_ledg.pack(side="left", padx=3)

                    btn_edit = ctk.CTkButton(
                        btn_box, text="Edit", width=55, height=24, font=Theme.FONT_CAPTION,
                        fg_color="transparent", hover_color=Theme.BG_TERTIARY,
                        border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR,
                        text_color=Theme.TEXT_PRIMARY,
                        command=lambda cid=row_id: self.open_edit_dialog(cid)
                    )
                    btn_edit.pack(side="left", padx=3)

                    btn_del = ctk.CTkButton(
                        btn_box, text="Delete", width=55, height=24, font=Theme.FONT_CAPTION,
                        fg_color="transparent", hover_color=Theme.DANGER_HOVER,
                        border_width=Theme.BORDER_WIDTH, border_color=Theme.DEBIT_RED,
                        text_color=Theme.DEBIT_RED,
                        command=lambda cid=row_id, name=cust['name']: self.confirm_delete_customer(cid, name)
                    )
                    btn_del.pack(side="left", padx=3)

        if not customers:
            empty_lbl = ctk.CTkLabel(
                self.scroll_frame,
                text="No customers match the active filters.",
                font=Theme.FONT_BODY,
                text_color=Theme.TEXT_SECONDARY
            )
            empty_lbl.grid(row=0, column=0, columnspan=4, pady=40)

    # ── Dialog helpers ────────────────────────────────────────────────────────

    def open_add_dialog(self):
        """Displays modal form for new customer addition."""
        CustomerFormDialog(self.winfo_toplevel(), self.customer_service, on_success=self.refresh_list)

    def open_import_wizard(self):
        """Launches the 5-step Excel Import Wizard dialog."""
        from ledger_app.ui.screens.import_wizard import ImportWizard
        ImportWizard(
            parent=self.winfo_toplevel(),
            customer_service=self.customer_service,
            transaction_service=self.transaction_service,
            payment_mode_repo=self.payment_mode_repo,
            backup_manager=self.backup_manager,
            import_mode="Customers",
            on_complete=lambda result: self.refresh_list()
        )

    def open_edit_dialog(self, customer_id: int):
        """Displays modal form for customer updates."""
        CustomerFormDialog(
            self.winfo_toplevel(), self.customer_service,
            customer_id=customer_id, on_success=self.refresh_list
        )

    def confirm_delete_customer(self, customer_id: int, name: str):
        """Requests user confirmation before performing cascade deletes."""
        title = "Confirm Deletion"
        message = (
            f"Are you sure you want to delete '{name}'?\n"
            "This will permanently clear all associated ledger transactions!"
        )
        if messagebox.askyesno(title, message, icon="warning"):
            try:
                self.customer_service.delete_customer(customer_id)
                self.refresh_list()
            except ValueError as e:
                messagebox.showerror("Error deleting customer", str(e))
                self.refresh_list()
