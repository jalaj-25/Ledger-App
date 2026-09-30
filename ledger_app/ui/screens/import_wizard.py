"""
import_wizard.py
================
5-Step Excel Import Wizard for Jalaj Ledger Management System.

Steps:
  1  Select File     — file picker + import type (Customers / Transactions)
  2  Preview Data    — scrollable raw-data table (first 20 rows)
  3  Map Columns     — dropdown per required field → Excel column
  4  Validate        — per-row validation results with error/warning list
  5  Import          — progress + summary panel

Usage:
    ImportWizard(
        parent          = self.winfo_toplevel(),
        customer_service  = ...,
        transaction_service = ...,
        payment_mode_repo = ...,
        backup_manager    = ...,
        import_mode       = "Customers",   # or "Transactions"
        on_complete       = callback_fn,   # called(result) after success
    )
"""

import os
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from typing import Optional, Callable

from ledger_app.ui.theme import Theme
from ledger_app.services.import_service import ImportService, ImportResult, ImportError

# ── Required fields per import type ─────────────────────────────────────────
CUSTOMER_FIELDS = [
    ("Name",            True,  "Customer's full name"),
    ("Phone",           False, "Phone number (10–15 digits)"),
    ("Address",         False, "Street / city address"),
    ("Opening Balance", False, "Starting balance amount"),
]

TRANSACTION_FIELDS = [
    ("Customer Name",   True,  "Must match an existing customer"),
    ("Type",            True,  "CREDIT / DEBIT / DAILY_CHARGE"),
    ("Amount",          True,  "Positive number"),
    ("Payment Mode",    False, "Cash / UPI / etc.  (required for CREDIT)"),
    ("Date",            False, "YYYY-MM-DD or DD/MM/YYYY"),
    ("Notes",           False, "Optional description / note"),
]

STEP_TITLES = [
    "Step 1 — Select File",
    "Step 2 — Preview Data",
    "Step 3 — Map Columns",
    "Step 4 — Validate",
    "Step 5 — Import",
]


# ════════════════════════════════════════════════════════════════════════════
#  ImportWizard — Main Dialog
# ════════════════════════════════════════════════════════════════════════════

class ImportWizard(ctk.CTkToplevel):
    """
    5-step Excel Import Wizard.  All steps live in a single window;
    step frames are shown/hidden with grid_forget / grid.
    """

    def __init__(
        self,
        parent,
        customer_service,
        transaction_service,
        payment_mode_repo,
        backup_manager=None,
        import_mode: str = "Customers",
        on_complete: Optional[Callable] = None,
    ):
        super().__init__(parent)
        self.customer_service    = customer_service
        self.transaction_service = transaction_service
        self.payment_mode_repo   = payment_mode_repo
        self.backup_manager      = backup_manager
        self.on_complete         = on_complete

        # ── State ─────────────────────────────────────────────────────────
        self._current_step  = 0
        self._filepath      = ""
        self._sheets        = None      # { sheet_name: DataFrame }
        self._sheet_name    = ""
        self._col_map       = {}        # { field_label: excel_col_name }
        self._valid_rows    = []
        self._errors        = []
        self._import_result: Optional[ImportResult] = None
        self._mode_var      = ctk.StringVar(value=import_mode)

        # ── Window setup ──────────────────────────────────────────────────
        self.title("Import Excel — Jalaj Ledger")
        width, height = 900, 620
        px = parent.winfo_x() + max(0, (parent.winfo_width() - width) // 2)
        py = parent.winfo_y() + max(0, (parent.winfo_height() - height) // 2)
        self.geometry(f"{width}x{height}+{px}+{py}")
        self.resizable(True, True)
        self.minsize(820, 540)
        self.configure(fg_color=Theme.BG_SECONDARY)
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Header (step indicator) ───────────────────────────────────────
        self._build_header()

        # ── Step container ────────────────────────────────────────────────
        self.step_container = ctk.CTkFrame(self, fg_color="transparent")
        self.step_container.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.step_container.grid_columnconfigure(0, weight=1)
        self.step_container.grid_rowconfigure(0, weight=1)

        # Build all step frames (hidden initially)
        self._step_frames = [
            self._build_step1(),
            self._build_step2(),
            self._build_step3(),
            self._build_step4(),
            self._build_step5(),
        ]

        # ── Footer navigation ─────────────────────────────────────────────
        self._build_footer()

        # Show first step
        self._show_step(0)

    # ── Header ───────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=Theme.BG_TERTIARY,
                            corner_radius=0, height=56)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(tuple(range(5)), weight=1)

        self._step_pills = []
        for i, title in enumerate(STEP_TITLES):
            short = title.split("—")[0].strip()
            pill = ctk.CTkLabel(
                hdr, text=short, font=Theme.FONT_CAPTION,
                text_color=Theme.TEXT_SECONDARY,
                fg_color="transparent"
            )
            pill.grid(row=0, column=i, sticky="nsew", padx=4, pady=8)
            self._step_pills.append(pill)

    def _update_step_pills(self, active: int):
        for i, pill in enumerate(self._step_pills):
            if i == active:
                pill.configure(
                    text_color=Theme.TEXT_WHITE,
                    fg_color=Theme.ACCENT
                )
            elif i < active:
                pill.configure(
                    text_color=Theme.CREDIT_GREEN,
                    fg_color="transparent"
                )
            else:
                pill.configure(
                    text_color=Theme.TEXT_SECONDARY,
                    fg_color="transparent"
                )

    # ── Footer ────────────────────────────────────────────────────────────────

    def _build_footer(self):
        sep = ctk.CTkFrame(self, fg_color=Theme.BORDER_COLOR, height=1)
        sep.grid(row=2, column=0, sticky="ew")

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=24, pady=(8, 16))
        footer.grid_columnconfigure(1, weight=1)

        self._status_lbl = ctk.CTkLabel(
            footer, text="", font=Theme.FONT_CAPTION,
            text_color=Theme.TEXT_SECONDARY, anchor="w", wraplength=480
        )
        self._status_lbl.grid(row=0, column=0, sticky="w")

        btn_box = ctk.CTkFrame(footer, fg_color="transparent")
        btn_box.grid(row=0, column=1, sticky="e")

        self._back_btn = ctk.CTkButton(
            btn_box, text="← Back", width=90, font=Theme.FONT_BODY_BOLD,
            fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY, state="disabled",
            command=self._on_back
        )
        self._back_btn.pack(side="left", padx=(0, 8))

        self._next_btn = ctk.CTkButton(
            btn_box, text="Next →", width=110, font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER,
            command=self._on_next
        )
        self._next_btn.pack(side="left", padx=(0, 8))

        self._cancel_btn = ctk.CTkButton(
            btn_box, text="Cancel", width=80, font=Theme.FONT_BODY_BOLD,
            fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY,
            command=self.destroy
        )
        self._cancel_btn.pack(side="left")

    # ── Step navigation ───────────────────────────────────────────────────────

    def _show_step(self, step: int):
        for i, frame in enumerate(self._step_frames):
            if i == step:
                frame.grid(row=0, column=0, sticky="nsew")
            else:
                frame.grid_forget()

        self._current_step = step
        self._update_step_pills(step)
        self._back_btn.configure(state="normal" if step > 0 else "disabled")

        # Adjust Next button label
        if step == 3:
            self._next_btn.configure(text="🔄  Validate")
        elif step == 4:
            self._next_btn.configure(text="✅  Import", fg_color=Theme.CREDIT_GREEN,
                                     hover_color="#16A34A")
        else:
            self._next_btn.configure(text="Next →", fg_color=Theme.ACCENT,
                                     hover_color=Theme.ACCENT_HOVER)

    def _on_back(self):
        if self._current_step > 0:
            self._show_step(self._current_step - 1)

    def _on_next(self):
        step = self._current_step
        if step == 0:
            self._advance_from_step1()
        elif step == 1:
            self._advance_from_step2()
        elif step == 2:
            self._advance_from_step3()
        elif step == 3:
            self._run_validate()
        elif step == 4:
            self._run_import()

    def _set_status(self, text: str, color=None):
        self._status_lbl.configure(
            text=text,
            text_color=color or Theme.TEXT_SECONDARY
        )

    # ════════════════════════════════════════════════════════════════════════
    #  STEP 1 — Select File
    # ════════════════════════════════════════════════════════════════════════

    def _build_step1(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.step_container, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(3, weight=1)

        # Title
        ctk.CTkLabel(
            frame, text="📂  Select Excel File",
            font=Theme.FONT_SUBTITLE, text_color=Theme.TEXT_PRIMARY, anchor="w"
        ).grid(row=0, column=0, sticky="w", padx=28, pady=(24, 4))

        ctk.CTkLabel(
            frame, text="Choose the .xlsx or .xls file you want to import from.",
            font=Theme.FONT_BODY, text_color=Theme.TEXT_SECONDARY, anchor="w"
        ).grid(row=1, column=0, sticky="w", padx=28, pady=(0, 16))

        # ── File picker row ────────────────────────────────────────────────
        pick_row = ctk.CTkFrame(frame, fg_color="transparent")
        pick_row.grid(row=2, column=0, sticky="ew", padx=28)
        pick_row.grid_columnconfigure(0, weight=1)

        self._filepath_entry = ctk.CTkEntry(
            pick_row, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS,
            placeholder_text="No file selected…", state="readonly"
        )
        self._filepath_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            pick_row, text="Browse…", font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER,
            width=90, command=self._browse_file
        ).grid(row=0, column=1)

        # ── Import type toggle ─────────────────────────────────────────────
        type_card = ctk.CTkFrame(
            frame, fg_color=Theme.BG_TERTIARY, corner_radius=10,
            border_width=1, border_color=Theme.BORDER_COLOR
        )
        type_card.grid(row=3, column=0, sticky="ew", padx=28, pady=(20, 0))
        type_card.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            type_card, text="Import Type", font=Theme.FONT_BODY_BOLD,
            text_color=Theme.TEXT_PRIMARY, anchor="w"
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 6))

        ctk.CTkRadioButton(
            type_card, text="👤  Customer List",
            font=Theme.FONT_BODY_BOLD, text_color=Theme.TEXT_PRIMARY,
            variable=self._mode_var, value="Customers",
            fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER,
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 14))

        ctk.CTkRadioButton(
            type_card, text="💰  Transactions",
            font=Theme.FONT_BODY_BOLD, text_color=Theme.TEXT_PRIMARY,
            variable=self._mode_var, value="Transactions",
            fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER,
        ).grid(row=1, column=1, sticky="w", padx=24, pady=(0, 14))

        # ── Sheet selector ─────────────────────────────────────────────────
        sheet_row = ctk.CTkFrame(frame, fg_color="transparent")
        sheet_row.grid(row=4, column=0, sticky="ew", padx=28, pady=(16, 0))
        sheet_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            sheet_row, text="Sheet:", font=Theme.FONT_BODY_BOLD,
            text_color=Theme.TEXT_PRIMARY
        ).grid(row=0, column=0, sticky="w", padx=(0, 10))

        self._sheet_var = ctk.StringVar(value="(load file first)")
        self._sheet_menu = ctk.CTkOptionMenu(
            sheet_row, variable=self._sheet_var,
            font=Theme.FONT_BODY, values=["(load file first)"],
            fg_color=Theme.BG_TERTIARY, button_color=Theme.ACCENT,
            text_color=Theme.TEXT_PRIMARY,
        )
        self._sheet_menu.grid(row=0, column=1, sticky="ew")

        return frame

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Select Excel File",
            filetypes=[("Excel Files", "*.xlsx *.xls *.xlsm"), ("All Files", "*.*")]
        )
        if not path:
            return
        self._filepath = path

        # Update entry widget
        self._filepath_entry.configure(state="normal")
        self._filepath_entry.delete(0, "end")
        self._filepath_entry.insert(0, path)
        self._filepath_entry.configure(state="readonly")

        # Parse file and update sheet list
        self._set_status("Loading file…")
        self.update()
        ok, sheets, msg = ImportService.parse_excel(path)
        if ok:
            self._sheets = sheets
            names = list(sheets.keys())
            self._sheet_var.set(names[0])
            self._sheet_menu.configure(values=names)
            self._set_status(f"✔  {msg}", color=Theme.CREDIT_GREEN)
        else:
            self._sheets = None
            self._set_status(f"❌  {msg}", color=Theme.DEBIT_RED)

    def _advance_from_step1(self):
        if not self._filepath or self._sheets is None:
            self._set_status("❌  Please select a valid Excel file first.", color=Theme.DEBIT_RED)
            return
        self._sheet_name = self._sheet_var.get()
        self._populate_step2()
        self._show_step(1)
        self._set_status("")

    # ════════════════════════════════════════════════════════════════════════
    #  STEP 2 — Preview Data
    # ════════════════════════════════════════════════════════════════════════

    def _build_step2(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.step_container, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        hdr = ctk.CTkFrame(frame, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=28, pady=(20, 4))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr, text="🔍  Preview Data",
            font=Theme.FONT_SUBTITLE, text_color=Theme.TEXT_PRIMARY, anchor="w"
        ).grid(row=0, column=0, sticky="w")

        self._preview_info_lbl = ctk.CTkLabel(
            hdr, text="", font=Theme.FONT_CAPTION,
            text_color=Theme.TEXT_SECONDARY, anchor="e"
        )
        self._preview_info_lbl.grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(
            frame, text="First 20 rows of your file — verify the data looks correct before mapping.",
            font=Theme.FONT_BODY, text_color=Theme.TEXT_SECONDARY, anchor="w"
        ).grid(row=1, column=0, sticky="w", padx=28, pady=(0, 10))

        # Scrollable preview table
        self._preview_scroll = ctk.CTkScrollableFrame(
            frame, fg_color=Theme.BG_TERTIARY,
            corner_radius=8, border_width=1, border_color=Theme.BORDER_COLOR
        )
        self._preview_scroll.grid(row=2, column=0, sticky="nsew", padx=28, pady=(0, 4))

        return frame

    def _populate_step2(self):
        # Clear old content
        for w in self._preview_scroll.winfo_children():
            w.destroy()

        cols = ImportService.get_column_names(self._sheets, self._sheet_name)
        rows = ImportService.get_preview_rows(self._sheets, self._sheet_name, max_rows=20)
        total_rows = len(self._sheets.get(self._sheet_name, []))

        self._preview_info_lbl.configure(
            text=f"{total_rows} data rows  •  {len(cols)} columns"
        )

        if not cols:
            ctk.CTkLabel(
                self._preview_scroll, text="No data found in this sheet.",
                font=Theme.FONT_BODY, text_color=Theme.TEXT_SECONDARY
            ).pack(pady=30)
            return

        # Configure columns
        for i, col in enumerate(cols):
            self._preview_scroll.grid_columnconfigure(i, minsize=120, weight=1)

        # Header row
        for i, col in enumerate(cols):
            ctk.CTkLabel(
                self._preview_scroll, text=str(col),
                font=Theme.FONT_BODY_BOLD, text_color=Theme.TEXT_PRIMARY,
                anchor="w"
            ).grid(row=0, column=i, sticky="ew", padx=8, pady=(8, 4))

        # Data rows
        for r, row_dict in enumerate(rows, start=1):
            bg = Theme.BG_SECONDARY if r % 2 == 0 else "transparent"
            for c, col in enumerate(cols):
                val = str(row_dict.get(col, ""))
                ctk.CTkLabel(
                    self._preview_scroll, text=val[:40],
                    font=Theme.FONT_CAPTION, text_color=Theme.TEXT_SECONDARY,
                    anchor="w"
                ).grid(row=r, column=c, sticky="ew", padx=8, pady=3)

    def _advance_from_step2(self):
        self._populate_step3()
        self._show_step(2)
        self._set_status("")

    # ════════════════════════════════════════════════════════════════════════
    #  STEP 3 — Map Columns
    # ════════════════════════════════════════════════════════════════════════

    def _build_step3(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.step_container, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            frame, text="🗂  Map Columns",
            font=Theme.FONT_SUBTITLE, text_color=Theme.TEXT_PRIMARY, anchor="w"
        ).grid(row=0, column=0, sticky="w", padx=28, pady=(24, 4))

        ctk.CTkLabel(
            frame,
            text="Match each required field to the corresponding Excel column header.",
            font=Theme.FONT_BODY, text_color=Theme.TEXT_SECONDARY, anchor="w"
        ).grid(row=1, column=0, sticky="w", padx=28, pady=(0, 12))

        self._mapping_scroll = ctk.CTkScrollableFrame(
            frame, fg_color="transparent"
        )
        self._mapping_scroll.grid(row=2, column=0, sticky="nsew", padx=28, pady=(0, 4))
        self._mapping_scroll.grid_columnconfigure(2, weight=1)

        return frame

    def _populate_step3(self):
        for w in self._mapping_scroll.winfo_children():
            w.destroy()

        mode = self._mode_var.get()
        fields = CUSTOMER_FIELDS if mode == "Customers" else TRANSACTION_FIELDS
        excel_cols = ImportService.get_column_names(self._sheets, self._sheet_name)
        optional_list = ["(skip)"] + excel_cols
        required_list = excel_cols if excel_cols else ["(no columns found)"]

        # Column headers
        for col_idx, hdr_text in enumerate(["Field", "Required", "Excel Column"]):
            ctk.CTkLabel(
                self._mapping_scroll, text=hdr_text,
                font=Theme.FONT_BODY_BOLD, text_color=Theme.TEXT_SECONDARY
            ).grid(row=0, column=col_idx, sticky="w", padx=8, pady=(0, 8))

        self._col_map_vars: Dict[str, ctk.StringVar] = {}

        for i, (field_label, required, hint) in enumerate(fields, start=1):
            # Field name
            req_marker = " *" if required else ""
            ctk.CTkLabel(
                self._mapping_scroll, text=f"{field_label}{req_marker}",
                font=Theme.FONT_BODY_BOLD, text_color=Theme.TEXT_PRIMARY
            ).grid(row=i, column=0, sticky="w", padx=8, pady=6)

            # Required badge
            badge_text = "Required" if required else "Optional"
            badge_color = Theme.WARNING_ORANGE if required else Theme.TEXT_SECONDARY
            ctk.CTkLabel(
                self._mapping_scroll, text=badge_text,
                font=Theme.FONT_CAPTION, text_color=badge_color
            ).grid(row=i, column=1, sticky="w", padx=12, pady=6)

            # Auto-detect matching column
            values = required_list if required else optional_list
            default_val = self._auto_detect_column(field_label, excel_cols, required)

            var = ctk.StringVar(value=default_val)
            self._col_map_vars[field_label] = var

            menu = ctk.CTkOptionMenu(
                self._mapping_scroll,
                variable=var, values=values,
                font=Theme.FONT_BODY,
                fg_color=Theme.BG_TERTIARY, button_color=Theme.ACCENT,
                text_color=Theme.TEXT_PRIMARY, width=220,
            )
            menu.grid(row=i, column=2, sticky="w", padx=8, pady=6)

            # Hint tooltip label
            ctk.CTkLabel(
                self._mapping_scroll, text=hint,
                font=Theme.FONT_CAPTION, text_color=Theme.TEXT_SECONDARY, anchor="w"
            ).grid(row=i, column=3, sticky="w", padx=16, pady=6)

    @staticmethod
    def _auto_detect_column(field_label: str, excel_cols, required: bool) -> str:
        """Fuzzy-match field name to an Excel column header."""
        label_lower = field_label.lower().replace(" ", "")
        for col in excel_cols:
            col_lower = col.lower().replace(" ", "").replace("_", "")
            if label_lower in col_lower or col_lower in label_lower:
                return col
        # Also check common aliases
        aliases = {
            "name":            ["customername", "client", "party"],
            "phone":           ["mobile", "contact", "tel"],
            "openingbalance":  ["balance", "openbal", "ob", "opening"],
            "type":            ["transtype", "txntype", "transactiontype", "kind"],
            "amount":          ["amt", "value", "sum"],
            "paymentmode":     ["mode", "payment", "modeofpayment"],
            "customername":    ["name", "client", "party"],
            "date":            ["txndate", "transdate", "transactiondate"],
        }
        for col in excel_cols:
            col_key = col.lower().replace(" ", "").replace("_", "")
            for alias in aliases.get(label_lower, []):
                if alias in col_key or col_key in alias:
                    return col
        return excel_cols[0] if (required and excel_cols) else "(skip)"

    def _advance_from_step3(self):
        # Build col_map
        col_map = {}
        for field_label, var in self._col_map_vars.items():
            val = var.get()
            if val != "(skip)":
                col_map[field_label] = val

        # Check required fields
        mode = self._mode_var.get()
        fields = CUSTOMER_FIELDS if mode == "Customers" else TRANSACTION_FIELDS
        missing = [f for f, req, _ in fields if req and f not in col_map]
        if missing:
            self._set_status(
                f"❌  Required fields not mapped: {', '.join(missing)}",
                color=Theme.DEBIT_RED
            )
            return

        self._col_map = col_map
        self._populate_step4()
        self._show_step(3)
        self._set_status("")

    # ════════════════════════════════════════════════════════════════════════
    #  STEP 4 — Validate
    # ════════════════════════════════════════════════════════════════════════

    def _build_step4(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.step_container, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        self._validate_hdr_lbl = ctk.CTkLabel(
            frame, text="✅  Validation Results",
            font=Theme.FONT_SUBTITLE, text_color=Theme.TEXT_PRIMARY, anchor="w"
        )
        self._validate_hdr_lbl.grid(row=0, column=0, sticky="w", padx=28, pady=(24, 4))

        self._validate_summary_lbl = ctk.CTkLabel(
            frame, text="Press 'Validate' to check your data.",
            font=Theme.FONT_BODY, text_color=Theme.TEXT_SECONDARY, anchor="w"
        )
        self._validate_summary_lbl.grid(row=1, column=0, sticky="w", padx=28, pady=(0, 10))

        # Error list scroll
        self._validate_scroll = ctk.CTkScrollableFrame(
            frame, fg_color=Theme.BG_TERTIARY,
            corner_radius=8, border_width=1, border_color=Theme.BORDER_COLOR
        )
        self._validate_scroll.grid(row=2, column=0, sticky="nsew", padx=28, pady=(0, 4))
        self._validate_scroll.grid_columnconfigure(0, weight=1)

        return frame

    def _populate_step4(self):
        for w in self._validate_scroll.winfo_children():
            w.destroy()
        self._validate_summary_lbl.configure(text="Press '🔄 Validate' to check your data.")

    def _run_validate(self):
        for w in self._validate_scroll.winfo_children():
            w.destroy()

        self._set_status("Validating…", color=Theme.TEXT_SECONDARY)
        self.update()

        mode = self._mode_var.get()
        if mode == "Customers":
            valid_rows, errors = ImportService.validate_customers(
                self._sheets, self._sheet_name, self._col_map
            )
        else:
            cname_map = ImportService.build_customer_name_map(self.customer_service)
            mode_map  = ImportService.build_payment_mode_map(self.payment_mode_repo)
            valid_rows, errors = ImportService.validate_transactions(
                self._sheets, self._sheet_name, self._col_map, cname_map, mode_map
            )

        self._valid_rows = valid_rows
        self._errors     = errors

        total = len(valid_rows) + len(errors)
        summary_text = (
            f"Total rows: {total}   ✅ Valid: {len(valid_rows)}   "
            f"❌ Errors: {len(errors)}"
        )
        color = Theme.CREDIT_GREEN if not errors else Theme.WARNING_ORANGE
        self._validate_summary_lbl.configure(text=summary_text, text_color=color)

        if not errors:
            ok_lbl = ctk.CTkLabel(
                self._validate_scroll,
                text="✅  All rows passed validation — ready to import!",
                font=Theme.FONT_BODY_BOLD, text_color=Theme.CREDIT_GREEN, anchor="w"
            )
            ok_lbl.grid(row=0, column=0, sticky="w", padx=16, pady=20)
        else:
            # Column headers
            for ci, htxt in enumerate(["Row", "Column", "Value", "Error"]):
                self._validate_scroll.grid_columnconfigure(ci, weight=1 if ci == 3 else 0,
                                                           minsize=[50, 100, 120, 300][ci])
                ctk.CTkLabel(
                    self._validate_scroll, text=htxt,
                    font=Theme.FONT_BODY_BOLD, text_color=Theme.TEXT_SECONDARY, anchor="w"
                ).grid(row=0, column=ci, sticky="w", padx=8, pady=(8, 4))

            for i, err in enumerate(errors, start=1):
                data = [str(err.row_number), err.column,
                        str(err.value)[:25], err.reason]
                colors = [Theme.TEXT_SECONDARY, Theme.TEXT_PRIMARY,
                          Theme.WARNING_ORANGE, Theme.DEBIT_RED]
                for ci, (val, col) in enumerate(zip(data, colors)):
                    ctk.CTkLabel(
                        self._validate_scroll, text=val,
                        font=Theme.FONT_CAPTION, text_color=col, anchor="w"
                    ).grid(row=i, column=ci, sticky="ew", padx=8, pady=3)

        if valid_rows:
            self._set_status(
                f"✔  {len(valid_rows)} valid rows ready. "
                f"Click 'Validate' again or proceed to Import.",
                color=Theme.CREDIT_GREEN
            )
            self._show_step(4)   # auto-advance to step 5
        else:
            self._set_status(
                "❌  No valid rows found. Fix errors in your file and re-load.",
                color=Theme.DEBIT_RED
            )

    # ════════════════════════════════════════════════════════════════════════
    #  STEP 5 — Import
    # ════════════════════════════════════════════════════════════════════════

    def _build_step5(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.step_container, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        self._import_status_lbl = ctk.CTkLabel(
            frame, text="📥  Ready to Import",
            font=Theme.FONT_SUBTITLE, text_color=Theme.TEXT_PRIMARY, anchor="w"
        )
        self._import_status_lbl.grid(row=0, column=0, sticky="w", padx=28, pady=(24, 4))

        # Central panel (progress + results)
        self._import_panel = ctk.CTkFrame(
            frame, fg_color=Theme.BG_TERTIARY,
            corner_radius=12, border_width=1, border_color=Theme.BORDER_COLOR
        )
        self._import_panel.grid(row=1, column=0, sticky="nsew", padx=28, pady=(4, 4))
        self._import_panel.grid_columnconfigure(0, weight=1)

        self._import_ready_lbl = ctk.CTkLabel(
            self._import_panel,
            text="Click  ✅ Import  to begin.\n\nA safety backup will be created automatically.",
            font=Theme.FONT_BODY, text_color=Theme.TEXT_SECONDARY, justify="center"
        )
        self._import_ready_lbl.pack(expand=True, pady=60)

        return frame

    def _run_import(self):
        if not self._valid_rows:
            self._set_status("❌  No valid rows to import.", color=Theme.DEBIT_RED)
            return

        mode = self._mode_var.get()

        # Disable buttons during import
        self._next_btn.configure(state="disabled", text="⏳  Importing…")
        self._back_btn.configure(state="disabled")
        self._cancel_btn.configure(state="disabled")

        # Clear panel
        for w in self._import_panel.winfo_children():
            w.destroy()

        self._progress_lbl = ctk.CTkLabel(
            self._import_panel, text="Creating safety backup…",
            font=Theme.FONT_BODY_BOLD, text_color=Theme.TEXT_SECONDARY
        )
        self._progress_lbl.pack(pady=(40, 12))

        self._progress_bar = ctk.CTkProgressBar(
            self._import_panel, mode="indeterminate",
            progress_color=Theme.ACCENT, width=400
        )
        self._progress_bar.pack(pady=(0, 40))
        self._progress_bar.start()

        self.update()

        # Run in background thread so UI stays alive
        threading.Thread(target=self._do_import_thread, daemon=True).start()

    def _do_import_thread(self):
        mode = self._mode_var.get()

        # ── Safety backup ────────────────────────────────────────────────
        if self.backup_manager:
            try:
                ok, msg = self.backup_manager.trigger_pre_operation_backup("Pre-Import")
                backup_note = f"Safety backup created." if ok else f"Backup skipped: {msg}"
            except Exception as be:
                backup_note = f"Backup warning: {be}"
        else:
            backup_note = "No backup manager — proceeding without backup."

        self.after(0, lambda: self._progress_lbl.configure(
            text=f"Importing {mode}…  ({backup_note})"
        ))

        # ── Perform import ───────────────────────────────────────────────
        try:
            if mode == "Customers":
                existing = ImportService.build_customer_name_map(self.customer_service)
                result = ImportService.import_customers(
                    self._valid_rows, self.customer_service, existing
                )
            else:
                mode_map = ImportService.build_payment_mode_map(self.payment_mode_repo)
                result = ImportService.import_transactions(
                    self._valid_rows, self.transaction_service,
                    self.payment_mode_repo, mode_map
                )
            self._import_result = result
        except Exception as e:
            result = ImportResult(import_type=mode, message=str(e), success=False)
            self._import_result = result

        self.after(0, lambda: self._show_import_summary(result))

    def _show_import_summary(self, result: ImportResult):
        self._progress_bar.stop()

        for w in self._import_panel.winfo_children():
            w.destroy()

        # ── Summary cards grid ────────────────────────────────────────────
        self._import_panel.grid_columnconfigure((0, 1), weight=1)

        # Big tick / cross
        icon_text = "✅" if result.success else "❌"
        status_text = "Import Completed!" if result.success else "Import Failed"
        status_color = Theme.CREDIT_GREEN if result.success else Theme.DEBIT_RED

        ctk.CTkLabel(
            self._import_panel, text=f"{icon_text}  {status_text}",
            font=Theme.FONT_SUBTITLE, text_color=status_color
        ).grid(row=0, column=0, columnspan=2, pady=(24, 16))

        # ── Stat tiles ────────────────────────────────────────────────────
        stats = [
            ("Rows Imported",  str(result.imported),    Theme.CREDIT_GREEN),
            ("Rows Skipped",   str(result.skipped),     Theme.WARNING_ORANGE),
            ("Validation Errors", str(result.error_count), Theme.DEBIT_RED),
            ("Total Rows",     str(result.total_rows),  Theme.TEXT_PRIMARY),
        ]
        for i, (label, value, color) in enumerate(stats):
            tile = ctk.CTkFrame(
                self._import_panel,
                fg_color=Theme.BG_SECONDARY, corner_radius=8,
                border_width=1, border_color=Theme.BORDER_COLOR
            )
            tile.grid(row=1 + i // 2, column=i % 2, padx=12, pady=6, sticky="ew")

            ctk.CTkLabel(tile, text=value, font=(Theme.FONT_FAMILY, 28, "bold"),
                         text_color=color).pack(pady=(12, 0))
            ctk.CTkLabel(tile, text=label, font=Theme.FONT_CAPTION,
                         text_color=Theme.TEXT_SECONDARY).pack(pady=(0, 12))

        # ── Warnings scroll ───────────────────────────────────────────────
        if result.warnings:
            warn_box = ctk.CTkScrollableFrame(
                self._import_panel, fg_color="transparent", height=90
            )
            warn_box.grid(row=3, column=0, columnspan=2, sticky="ew", padx=12, pady=(4, 0))
            for w_text in result.warnings[:10]:
                ctk.CTkLabel(
                    warn_box, text=f"⚠  {w_text}",
                    font=Theme.FONT_CAPTION, text_color=Theme.WARNING_ORANGE,
                    anchor="w"
                ).pack(anchor="w", pady=1)

        # ── Errors scroll ─────────────────────────────────────────────────
        if result.errors:
            err_box = ctk.CTkScrollableFrame(
                self._import_panel, fg_color="transparent", height=80
            )
            err_box.grid(row=4, column=0, columnspan=2, sticky="ew", padx=12, pady=(4, 8))
            for err in result.errors[:10]:
                ctk.CTkLabel(
                    err_box,
                    text=f"❌  Row {err.row_number} [{err.column}]: {err.reason}",
                    font=Theme.FONT_CAPTION, text_color=Theme.DEBIT_RED, anchor="w"
                ).pack(anchor="w", pady=1)

        # ── Footer buttons ────────────────────────────────────────────────
        self._next_btn.configure(state="disabled", text="✅  Done")
        self._back_btn.configure(state="disabled")
        self._cancel_btn.configure(state="normal", text="Close")

        self._set_status(result.message,
                         color=Theme.CREDIT_GREEN if result.success else Theme.DEBIT_RED)
        self._import_status_lbl.configure(text=f"📥  {status_text}")

        # Fire callback so parent can refresh its list
        if result.success and self.on_complete:
            try:
                self.on_complete(result)
            except Exception:
                pass


# ════════════════════════════════════════════════════════════════════════════
#  ImportScreen — persistent frame shown in the main app sidebar slot
# ════════════════════════════════════════════════════════════════════════════

class ImportScreen(ctk.CTkFrame):
    """
    Lightweight landing screen for the "Import Excel" sidebar item.
    Shows import history and a Launch Wizard button.
    """

    def __init__(
        self,
        parent,
        customer_service,
        transaction_service,
        payment_mode_repo,
        backup_manager=None,
        on_import_complete=None,
    ):
        super().__init__(parent, fg_color="transparent")
        self.customer_service    = customer_service
        self.transaction_service = transaction_service
        self.payment_mode_repo   = payment_mode_repo
        self.backup_manager      = backup_manager
        self.on_import_complete  = on_import_complete
        self._history: list      = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Header ────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr, text="Import Excel",
            font=Theme.FONT_TITLE, text_color=Theme.TEXT_PRIMARY, anchor="w"
        ).grid(row=0, column=0, sticky="w")

        self._launch_btn = ctk.CTkButton(
            hdr, text="📥  Launch Import Wizard",
            font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER,
            command=self._open_wizard
        )
        self._launch_btn.grid(row=0, column=1, sticky="e")

        # ── Info cards row ────────────────────────────────────────────────
        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.grid(row=0, column=0, sticky="ew", pady=(60, 0))
        cards.grid_columnconfigure((0, 1), weight=1)

        self._build_info_card(
            cards, col=0,
            icon="👤", title="Customer Import",
            desc=(
                "Bulk import customers from Excel.\n\n"
                "Required columns:\n"
                "  • Name\n\n"
                "Optional columns:\n"
                "  • Phone\n"
                "  • Address\n"
                "  • Opening Balance"
            )
        )
        self._build_info_card(
            cards, col=1,
            icon="💰", title="Transaction Import",
            desc=(
                "Bulk import transactions from Excel.\n\n"
                "Required columns:\n"
                "  • Customer Name\n"
                "  • Type  (CREDIT / DEBIT / DAILY_CHARGE)\n"
                "  • Amount\n\n"
                "Optional columns:\n"
                "  • Payment Mode\n"
                "  • Date\n"
                "  • Notes"
            )
        )

        # ── History section ───────────────────────────────────────────────
        sep = ctk.CTkFrame(self, fg_color=Theme.BORDER_COLOR, height=1)
        sep.grid(row=1, column=0, sticky="ew", pady=(20, 8))

        ctk.CTkLabel(
            self, text="Import History  (this session)",
            font=Theme.FONT_BODY_BOLD, text_color=Theme.TEXT_SECONDARY, anchor="w"
        ).grid(row=2, column=0, sticky="w", pady=(0, 4))

        self._history_frame = ctk.CTkScrollableFrame(
            self, fg_color=Theme.BG_TERTIARY,
            corner_radius=8, border_width=1, border_color=Theme.BORDER_COLOR
        )
        self._history_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 4))
        self.grid_rowconfigure(3, weight=1)

        self._empty_history_lbl = ctk.CTkLabel(
            self._history_frame,
            text="No imports yet this session.",
            font=Theme.FONT_BODY, text_color=Theme.TEXT_SECONDARY
        )
        self._empty_history_lbl.pack(pady=30)

    @staticmethod
    def _build_info_card(parent, col: int, icon: str, title: str, desc: str):
        card = ctk.CTkFrame(
            parent, fg_color=Theme.BG_SECONDARY,
            corner_radius=12, border_width=1, border_color=Theme.BORDER_COLOR
        )
        card.grid(row=0, column=col, padx=10, pady=4, sticky="nsew")

        ctk.CTkLabel(
            card, text=icon, font=(Theme.FONT_FAMILY, 32)
        ).pack(pady=(20, 4))
        ctk.CTkLabel(
            card, text=title, font=Theme.FONT_SUBTITLE,
            text_color=Theme.TEXT_PRIMARY
        ).pack(pady=(0, 8))
        ctk.CTkLabel(
            card, text=desc, font=Theme.FONT_CAPTION,
            text_color=Theme.TEXT_SECONDARY, justify="left", anchor="w", wraplength=300
        ).pack(padx=20, pady=(0, 20), anchor="w")

    def _open_wizard(self):
        ImportWizard(
            parent=self.winfo_toplevel(),
            customer_service=self.customer_service,
            transaction_service=self.transaction_service,
            payment_mode_repo=self.payment_mode_repo,
            backup_manager=self.backup_manager,
            import_mode="Customers",
            on_complete=self._on_wizard_complete,
        )

    def _on_wizard_complete(self, result: ImportResult):
        import datetime as dt
        self._history.append(result)
        self._refresh_history()
        if self.on_import_complete:
            try:
                self.on_import_complete(result)
            except Exception:
                pass

    def _refresh_history(self):
        for w in self._history_frame.winfo_children():
            w.destroy()

        if not self._history:
            self._empty_history_lbl = ctk.CTkLabel(
                self._history_frame,
                text="No imports yet this session.",
                font=Theme.FONT_BODY, text_color=Theme.TEXT_SECONDARY
            )
            self._empty_history_lbl.pack(pady=30)
            return

        for i, result in enumerate(reversed(self._history)):
            row = ctk.CTkFrame(
                self._history_frame, fg_color="transparent", corner_radius=6
            )
            row.pack(fill="x", pady=2, padx=8)

            icon = "✅" if result.success else "❌"
            summary = (
                f"{icon}  {result.import_type}   —   "
                f"Imported: {result.imported}  |  "
                f"Skipped: {result.skipped}  |  "
                f"Errors: {result.error_count}"
            )
            color = Theme.CREDIT_GREEN if result.success else Theme.DEBIT_RED
            ctk.CTkLabel(
                row, text=summary,
                font=Theme.FONT_BODY, text_color=color, anchor="w"
            ).pack(side="left", padx=8, pady=6)

    def refresh(self):
        """Called by app shell when this screen becomes active."""
        pass
