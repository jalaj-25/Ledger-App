import customtkinter as ctk
import os
import shutil
import json
import datetime
import subprocess
from tkinter import filedialog, messagebox
from ledger_app.ui.theme import Theme
from ledger_app.ui.theme_manager import ThemeManager
from ledger_app.database.db_connection import DatabaseManager
from ledger_app.services.pdf_security_service import PdfSecurityService

SETTINGS_FILE = "settings.json"

class ThemePreviewCard(ctk.CTkFrame):
    """A visual card displaying a mini app layout preview for a specific theme."""
    def __init__(self, parent, theme_name: str, bg_color: str, sidebar_color: str, 
                 card_color: str, accent_color: str, border_color: str, 
                 text_color: str, is_selected: bool, command: callable):
        
        border_w = 3 if is_selected else 1
        b_color = accent_color if is_selected else border_color
        
        super().__init__(
            parent, 
            fg_color=card_color, 
            corner_radius=10, 
            border_width=border_w, 
            border_color=b_color
        )
        self.command = command
        self.accent_color = accent_color
        self.border_color = border_color
        self.is_selected = is_selected
        
        # Configure layout
        self.grid_columnconfigure(0, weight=1)
        
        # Make card clickable
        self.bind("<Button-1>", lambda e: self.command())
        
        # Mini App preview container
        preview_container = ctk.CTkFrame(
            self,
            fg_color=bg_color,
            height=90,
            width=150,
            corner_radius=6,
            border_width=1,
            border_color=border_color
        )
        preview_container.pack(padx=15, pady=(15, 8))
        preview_container.pack_propagate(False)
        preview_container.bind("<Button-1>", lambda e: self.command())
        
        # Grid layout for mini app layout: Col 0 sidebar, Col 1 content
        preview_container.grid_columnconfigure(0, weight=0)
        preview_container.grid_columnconfigure(1, weight=1)
        preview_container.grid_rowconfigure(0, weight=1)
        
        # Mini Sidebar
        mini_sidebar = ctk.CTkFrame(
            preview_container,
            fg_color=sidebar_color,
            width=35,
            corner_radius=0,
            border_width=0
        )
        mini_sidebar.grid(row=0, column=0, sticky="nsew")
        mini_sidebar.grid_propagate(False)
        mini_sidebar.bind("<Button-1>", lambda e: self.command())
        
        # Mini Sidebar Items
        for i in range(3):
            line = ctk.CTkFrame(
                mini_sidebar,
                fg_color=accent_color if i == 0 else border_color,
                height=3,
                width=18,
                corner_radius=1
            )
            line.pack(pady=4, padx=8)
            line.bind("<Button-1>", lambda e: self.command())
            
        # Mini Content Area
        mini_content = ctk.CTkFrame(
            preview_container,
            fg_color=bg_color,
            corner_radius=0,
            border_width=0
        )
        mini_content.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        mini_content.bind("<Button-1>", lambda e: self.command())
        
        # Mini KPI Row
        kpi_row = ctk.CTkFrame(mini_content, fg_color="transparent")
        kpi_row.pack(fill="x", pady=(0, 4))
        kpi_row.bind("<Button-1>", lambda e: self.command())
        
        for _ in range(2):
            mini_card = ctk.CTkFrame(
                kpi_row,
                fg_color=card_color,
                height=15,
                width=42,
                corner_radius=2,
                border_width=0.5,
                border_color=border_color
            )
            mini_card.pack(side="left", padx=1)
            mini_card.bind("<Button-1>", lambda e: self.command())
            
        # Mini Table Box
        mini_table = ctk.CTkFrame(
            mini_content,
            fg_color=card_color,
            height=30,
            corner_radius=3,
            border_width=0.5,
            border_color=border_color
        )
        mini_table.pack(fill="both", expand=True)
        mini_table.pack_propagate(False)
        mini_table.bind("<Button-1>", lambda e: self.command())
        
        # Mini Table lines
        for _ in range(2):
            t_line = ctk.CTkFrame(
                mini_table,
                fg_color=border_color,
                height=2,
                corner_radius=1
            )
            t_line.pack(fill="x", pady=3, padx=5)
            t_line.bind("<Button-1>", lambda e: self.command())

        # Title Label with Checkmark icon
        lbl_text = theme_name.upper()
        if is_selected:
            lbl_text += "  ✓"
            
        self.lbl = ctk.CTkLabel(
            self, 
            text=lbl_text, 
            font=Theme.FONT_BODY_BOLD,
            text_color=accent_color if is_selected else text_color
        )
        self.lbl.pack(side="top", anchor="center", pady=(0, 12))
        self.lbl.bind("<Button-1>", lambda e: self.command())
        
        # Hover events
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        
    def on_enter(self, event):
        self.configure(border_color=self.accent_color)
        
    def on_leave(self, event):
        if not self.is_selected:
            self.configure(border_color=self.border_color)


class SettingsScreen(ctk.CTkFrame):
    """View Screen for configuring business profiles, notifications, and performing backups."""
    def __init__(self, parent, db_manager: DatabaseManager, customer_service,
                 transaction_service, report_service, on_db_reset: callable,
                 backup_manager=None):
        super().__init__(parent, fg_color="transparent")

        self.db_manager = db_manager
        self.customer_service = customer_service
        self.transaction_service = transaction_service
        self.report_service = report_service
        self.on_db_reset = on_db_reset
        self.backup_manager = backup_manager

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. Header Frame Row
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))

        self.title_lbl = ctk.CTkLabel(
            self.header_frame,
            text="Settings & Preferences",
            font=Theme.FONT_TITLE,
            text_color=Theme.TEXT_PRIMARY,
            anchor="w"
        )
        self.title_lbl.pack(side="left")

        # Scrollable grid container
        self.cards_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.cards_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        self.cards_frame.grid_columnconfigure((0, 1), weight=1, uniform="settings_cols")

        # Create all Settings Cards
        self.create_theme_card()
        self.create_profile_card()
        self.create_notifications_card()
        self.create_backup_card()          # ← fully replaced
        self.create_report_settings_card()
        self.create_about_card()
        self.create_pdf_security_card()
        self.create_email_settings_card()

        # Load values into UI
        self.load_settings(load_profile_entries=True)
        self.update_about_stats()

    def create_theme_card(self):
        """🎨 Theme Selection Card"""
        self.theme_card = ctk.CTkFrame(
            self.cards_frame,
            fg_color=Theme.BG_SECONDARY,
            corner_radius=12,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR
        )
        self.theme_card.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.theme_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.theme_card,
            text="🎨 THEME SELECTION",
            font=Theme.FONT_SUBTITLE,
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w", padx=20, pady=(15, 10))

        self.theme_previews_box = ctk.CTkFrame(self.theme_card, fg_color="transparent")
        self.theme_previews_box.pack(fill="x", padx=20, pady=(0, 15))
        self.theme_previews_box.grid_columnconfigure((0, 1), weight=1)

    def draw_theme_previews(self, current_theme: str):
        """Re-draws Light & Dark mode visual preview cards based on selection state."""
        for widget in self.theme_previews_box.winfo_children():
            widget.destroy()

        light_preview = ThemePreviewCard(
            self.theme_previews_box,
            theme_name="Light Mode",
            bg_color="#F8FAFC",
            sidebar_color="#FFFFFF",
            card_color="#FFFFFF",
            accent_color="#0EA5E9",
            border_color="#E2E8F0",
            text_color="#0F172A",
            is_selected=(current_theme == "light"),
            command=lambda: self.change_theme("light")
        )
        light_preview.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        dark_preview = ThemePreviewCard(
            self.theme_previews_box,
            theme_name="Dark Mode",
            bg_color="#0B1220",
            sidebar_color="#111827",
            card_color="#1E293B",
            accent_color="#14B8A6",
            border_color="#334155",
            text_color="#F8FAFC",
            is_selected=(current_theme == "dark"),
            command=lambda: self.change_theme("dark")
        )
        dark_preview.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

    def create_profile_card(self):
        """💼 Business Profile Card"""
        self.profile_card = ctk.CTkFrame(
            self.cards_frame,
            fg_color=Theme.BG_SECONDARY,
            corner_radius=12,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR
        )
        self.profile_card.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.profile_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.profile_card,
            text="💼 BUSINESS PROFILE",
            font=Theme.FONT_SUBTITLE,
            text_color=Theme.TEXT_PRIMARY
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(15, 10))

        ctk.CTkLabel(self.profile_card, text="Business Name", font=Theme.FONT_BODY_BOLD).grid(row=1, column=0, sticky="w", padx=20, pady=6)
        self.biz_name_entry = ctk.CTkEntry(self.profile_card, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS)
        self.biz_name_entry.grid(row=1, column=1, sticky="ew", padx=(10, 20), pady=6)

        ctk.CTkLabel(self.profile_card, text="Owner Name", font=Theme.FONT_BODY_BOLD).grid(row=2, column=0, sticky="w", padx=20, pady=6)
        self.biz_owner_entry = ctk.CTkEntry(self.profile_card, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS)
        self.biz_owner_entry.grid(row=2, column=1, sticky="ew", padx=(10, 20), pady=6)

        ctk.CTkLabel(self.profile_card, text="Phone Number", font=Theme.FONT_BODY_BOLD).grid(row=3, column=0, sticky="w", padx=20, pady=6)
        self.biz_phone_entry = ctk.CTkEntry(self.profile_card, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS)
        self.biz_phone_entry.grid(row=3, column=1, sticky="ew", padx=(10, 20), pady=6)

        ctk.CTkLabel(self.profile_card, text="Address", font=Theme.FONT_BODY_BOLD).grid(row=4, column=0, sticky="w", padx=20, pady=6)
        self.biz_addr_entry = ctk.CTkEntry(self.profile_card, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS)
        self.biz_addr_entry.grid(row=4, column=1, sticky="ew", padx=(10, 20), pady=6)

        self.save_profile_btn = ctk.CTkButton(
            self.profile_card, text="Save Changes", font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER, command=self.save_profile
        )
        self.save_profile_btn.grid(row=5, column=1, sticky="e", padx=(0, 20), pady=(10, 15))

    def create_notifications_card(self):
        """🔔 Notification Preferences Card"""
        self.notifications_card = ctk.CTkFrame(
            self.cards_frame,
            fg_color=Theme.BG_SECONDARY,
            corner_radius=12,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR
        )
        self.notifications_card.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.notifications_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.notifications_card,
            text="🔔 NOTIFICATION PREFERENCES",
            font=Theme.FONT_SUBTITLE,
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w", padx=20, pady=(15, 10))

        self.startup_notify_var = ctk.BooleanVar(value=True)
        self.startup_notify_sw = ctk.CTkSwitch(
            self.notifications_card, text="Startup Notification",
            variable=self.startup_notify_var, font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.BORDER_COLOR, progress_color=Theme.ACCENT, command=self.save_notifications
        )
        self.startup_notify_sw.pack(anchor="w", padx=30, pady=8)

        self.shutdown_notify_var = ctk.BooleanVar(value=True)
        self.shutdown_notify_sw = ctk.CTkSwitch(
            self.notifications_card, text="Shutdown Notification",
            variable=self.shutdown_notify_var, font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.BORDER_COLOR, progress_color=Theme.ACCENT, command=self.save_notifications
        )
        self.shutdown_notify_sw.pack(anchor="w", padx=30, pady=8)

        self.daily_report_var = ctk.BooleanVar(value=True)
        self.daily_report_sw = ctk.CTkSwitch(
            self.notifications_card, text="Generate Daily Report PDF",
            variable=self.daily_report_var, font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.BORDER_COLOR, progress_color=Theme.ACCENT, command=self.save_notifications
        )
        self.daily_report_sw.pack(anchor="w", padx=30, pady=8)

        self.wa_delivery_var = ctk.BooleanVar(value=False)
        self.wa_delivery_sw = ctk.CTkSwitch(
            self.notifications_card, text="WhatsApp Report Delivery",
            variable=self.wa_delivery_var, font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.BORDER_COLOR, progress_color=Theme.ACCENT, command=self.save_notifications
        )
        self.wa_delivery_sw.pack(anchor="w", padx=30, pady=(8, 20))

    # ================================================================== #
    #  Backup & Recovery Card  (fully redesigned)
    # ================================================================== #

    def create_backup_card(self):
        """💾 Backup & Recovery Card — full-featured backup management UI."""
        self.backup_card = ctk.CTkFrame(
            self.cards_frame,
            fg_color=Theme.BG_SECONDARY,
            corner_radius=12,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR
        )
        self.backup_card.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        self.backup_card.grid_columnconfigure(0, weight=1)

        # ── Card Header ──────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self.backup_card, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 0))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr, text="💾", font=(Theme.FONT_FAMILY, 20)
        ).grid(row=0, column=0, padx=(0, 8))

        ctk.CTkLabel(
            hdr, text="BACKUP & RECOVERY",
            font=Theme.FONT_SUBTITLE,
            text_color=Theme.TEXT_PRIMARY,
            anchor="w"
        ).grid(row=0, column=1, sticky="w")

        # Auto-backup status pill (right side)
        self.backup_status_pill = ctk.CTkLabel(
            hdr, text="● AUTO ON",
            font=Theme.FONT_BODY_BOLD,
            text_color="#22C55E"
        )
        self.backup_status_pill.grid(row=0, column=2, sticky="e")

        # ── Separator ────────────────────────────────────────────────────
        ctk.CTkFrame(self.backup_card, fg_color=Theme.BORDER_COLOR, height=1).grid(
            row=1, column=0, sticky="ew", padx=20, pady=(10, 0)
        )

        # ── Status Info Panel ─────────────────────────────────────────────
        status_panel = ctk.CTkFrame(
            self.backup_card,
            fg_color=Theme.BG_TERTIARY,
            corner_radius=8,
            border_width=1,
            border_color=Theme.BORDER_COLOR
        )
        status_panel.grid(row=2, column=0, sticky="ew", padx=20, pady=(12, 8))
        status_panel.grid_columnconfigure(1, weight=1)

        # Status rows
        status_items = [
            ("Last Backup", "last_backup_date_lbl", "Never"),
            ("Backup Type", "last_backup_type_lbl", "—"),
            ("Backup Location", "backup_location_lbl", "backups/"),
            ("Retention Limit", "retention_lbl", "30 backups"),
        ]
        for i, (label, attr, default) in enumerate(status_items):
            ctk.CTkLabel(
                status_panel, text=label,
                font=Theme.FONT_BODY_BOLD,
                text_color=Theme.TEXT_SECONDARY,
                anchor="w"
            ).grid(row=i, column=0, sticky="w", padx=(12, 8), pady=4)

            val_lbl = ctk.CTkLabel(
                status_panel, text=default,
                font=Theme.FONT_BODY,
                text_color=Theme.TEXT_PRIMARY,
                anchor="e",
                wraplength=180
            )
            val_lbl.grid(row=i, column=1, sticky="ew", padx=(0, 12), pady=4)
            setattr(self, attr, val_lbl)

        # ── Auto-Backup Toggle ────────────────────────────────────────────
        auto_row = ctk.CTkFrame(self.backup_card, fg_color="transparent")
        auto_row.grid(row=3, column=0, sticky="ew", padx=20, pady=(4, 0))

        self.auto_backup_var = ctk.BooleanVar(value=True)
        self.auto_backup_sw = ctk.CTkSwitch(
            auto_row,
            text="Automatic Daily & Shutdown Backup",
            variable=self.auto_backup_var,
            font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.BORDER_COLOR,
            progress_color=Theme.ACCENT,
            command=self._on_auto_backup_toggle
        )
        self.auto_backup_sw.pack(anchor="w")

        # ── Action Buttons ────────────────────────────────────────────────
        btn_grid = ctk.CTkFrame(self.backup_card, fg_color="transparent")
        btn_grid.grid(row=4, column=0, sticky="ew", padx=20, pady=(10, 4))
        btn_grid.grid_columnconfigure((0, 1), weight=1)

        # Row 1
        self.backup_now_btn = ctk.CTkButton(
            btn_grid, text="💾  Backup Now",
            font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER,
            command=self._on_backup_now
        )
        self.backup_now_btn.grid(row=0, column=0, padx=(0, 5), pady=4, sticky="ew")

        self.restore_btn = ctk.CTkButton(
            btn_grid, text="🔄  Restore Backup",
            font=Theme.FONT_BODY_BOLD,
            fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY,
            command=self._on_open_restore_dialog
        )
        self.restore_btn.grid(row=0, column=1, padx=(5, 0), pady=4, sticky="ew")

        # Row 2
        self.open_folder_btn = ctk.CTkButton(
            btn_grid, text="📂  Open Backup Folder",
            font=Theme.FONT_BODY_BOLD,
            fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY,
            command=self.open_backup_folder
        )
        self.open_folder_btn.grid(row=1, column=0, padx=(0, 5), pady=4, sticky="ew")

        self.change_location_btn = ctk.CTkButton(
            btn_grid, text="📁  Change Backup Location",
            font=Theme.FONT_BODY_BOLD,
            fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY,
            command=self._on_change_backup_location
        )
        self.change_location_btn.grid(row=1, column=1, padx=(5, 0), pady=4, sticky="ew")

        # Row 3 — History (full width)
        self.history_btn = ctk.CTkButton(
            btn_grid, text="📋  View Backup History",
            font=Theme.FONT_BODY_BOLD,
            fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY,
            command=self._on_open_history_dialog
        )
        self.history_btn.grid(row=2, column=0, columnspan=2, pady=4, sticky="ew")

        # ── Feedback label ────────────────────────────────────────────────
        self.backup_msg_lbl = ctk.CTkLabel(
            self.backup_card, text="",
            font=Theme.FONT_CAPTION,
            text_color=Theme.TEXT_SECONDARY,
            anchor="w", wraplength=350
        )
        self.backup_msg_lbl.grid(row=5, column=0, sticky="w", padx=20, pady=(4, 2))

        # ── Danger Zone separator ─────────────────────────────────────────
        ctk.CTkFrame(self.backup_card, fg_color=Theme.BORDER_COLOR, height=1).grid(
            row=6, column=0, sticky="ew", padx=20, pady=(10, 0)
        )
        ctk.CTkLabel(
            self.backup_card, text="⚠  DANGER ZONE",
            font=Theme.FONT_CAPTION,
            text_color=Theme.WARNING_ORANGE,
            anchor="w"
        ).grid(row=7, column=0, sticky="w", padx=20, pady=(6, 2))

        self.purge_btn = ctk.CTkButton(
            self.backup_card, text="🚨  Clear All Data",
            font=Theme.FONT_BODY_BOLD,
            fg_color="transparent", hover_color=Theme.DANGER_HOVER,
            border_width=Theme.BORDER_WIDTH, border_color=Theme.DEBIT_RED,
            text_color=Theme.DEBIT_RED,
            command=self.purge_database
        )
        self.purge_btn.grid(row=8, column=0, padx=20, pady=(4, 15), sticky="ew")

    # ── Backup Card event handlers ────────────────────────────────────────

    def _on_backup_now(self):
        """Triggers a manual backup and updates status."""
        if not self.backup_manager:
            messagebox.showerror("Unavailable", "Backup manager not initialized.")
            return
        self.backup_now_btn.configure(state="disabled", text="⏳  Creating backup...")
        self.update()

        success, msg = self.backup_manager.trigger_manual_backup()

        self.backup_now_btn.configure(state="normal", text="💾  Backup Now")
        if success:
            self._show_backup_msg(f"✔  {msg}", color="#22C55E")
            self._refresh_backup_status()
        else:
            self._show_backup_msg(f"❌  {msg}", color="#EF4444")

    def _on_auto_backup_toggle(self):
        """Saves auto_backup_enabled to settings.json and refreshes the pill."""
        if not self.backup_manager:
            return
        enabled = self.auto_backup_var.get()
        self.backup_manager.set_auto_backup_enabled(enabled)
        self._update_auto_backup_pill(enabled)

    def _on_change_backup_location(self):
        """Opens a folder picker and updates the backup folder setting."""
        folder = filedialog.askdirectory(title="Select Backup Storage Folder")
        if not folder:
            return
        if not self.backup_manager:
            return
        ok, msg = self.backup_manager.set_backup_folder(folder)
        if ok:
            self._show_backup_msg(f"✔  Backup location changed to: {folder}", color="#22C55E")
            self._refresh_backup_status()
        else:
            self._show_backup_msg(f"❌  {msg}", color="#EF4444")

    def _on_open_history_dialog(self):
        """Opens the Backup History modal dialog."""
        if not self.backup_manager:
            messagebox.showerror("Unavailable", "Backup manager not initialized.")
            return
        BackupHistoryDialog(
            parent=self.winfo_toplevel(),
            backup_manager=self.backup_manager,
            on_restore_request=self._handle_restore_from_history
        )

    def _on_open_restore_dialog(self):
        """Opens the Restore Backup guided dialog."""
        if not self.backup_manager:
            messagebox.showerror("Unavailable", "Backup manager not initialized.")
            return
        BackupRestoreDialog(
            parent=self.winfo_toplevel(),
            backup_manager=self.backup_manager,
            db_path=self.db_manager.db_path,
            on_restore_complete=self._on_restore_complete
        )

    def _handle_restore_from_history(self, zip_path: str):
        """Triggered by BackupHistoryDialog when user clicks Restore on a row."""
        BackupRestoreDialog(
            parent=self.winfo_toplevel(),
            backup_manager=self.backup_manager,
            db_path=self.db_manager.db_path,
            on_restore_complete=self._on_restore_complete,
            preselected_zip=zip_path
        )

    def _on_restore_complete(self, success: bool, message: str):
        """Called after a restore operation completes."""
        if success:
            self._refresh_backup_status()
            self.update_about_stats()
            self.on_db_reset()

    def open_backup_folder(self):
        """Opens the backup folder in the OS file manager."""
        if self.backup_manager:
            backup_dir = self.backup_manager.get_backup_dir()
        else:
            backup_dir = "backups"
        abs_dir = os.path.abspath(backup_dir)
        os.makedirs(abs_dir, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(abs_dir)
            else:
                subprocess.Popen(["xdg-open", abs_dir])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")

    def purge_database(self):
        """Deletes all records from customers and transactions after a safety backup."""
        confirm = messagebox.askyesno(
            "Confirm Clear All Data",
            "Are you absolutely sure you want to delete ALL customer records and transactions?\n\n"
            "A safety backup will be created first, but this action is irreversible!",
            icon="warning"
        )
        if not confirm:
            return

        # Pre-operation safety backup
        if self.backup_manager:
            ok, msg = self.backup_manager.trigger_pre_operation_backup("Pre-Delete")
            if not ok:
                proceed = messagebox.askyesno(
                    "Safety Backup Failed",
                    f"Could not create a safety backup:\n{msg}\n\nDo you still want to proceed with clearing all data?",
                    icon="warning"
                )
                if not proceed:
                    return

        try:
            with self.db_manager.get_connection() as conn:
                conn.execute("DELETE FROM transactions;")
                conn.execute("DELETE FROM customers;")
                conn.execute("DELETE FROM sqlite_sequence;")

            messagebox.showinfo("Clean Completed", "All database tables cleared successfully!")
            self.update_about_stats()
            self.on_db_reset()
        except Exception as e:
            messagebox.showerror("Operation Failed", f"Database purge failed: {e}")

    def _refresh_backup_status(self):
        """Updates the status panel labels with fresh data from BackupManager."""
        if not self.backup_manager:
            return
        info = self.backup_manager.get_last_backup_info()
        self.last_backup_date_lbl.configure(text=info.get("last_backup_date", "Never"))
        self.last_backup_type_lbl.configure(text=info.get("last_backup_type", "—"))

        folder = self.backup_manager.get_backup_dir()
        # Truncate long paths for display
        display_folder = folder if len(folder) <= 35 else "..." + folder[-32:]
        self.backup_location_lbl.configure(text=display_folder)

        enabled = self.backup_manager.is_auto_backup_enabled()
        self.auto_backup_var.set(enabled)
        self._update_auto_backup_pill(enabled)

    def _update_auto_backup_pill(self, enabled: bool):
        if enabled:
            self.backup_status_pill.configure(text="● AUTO ON", text_color="#22C55E")
        else:
            self.backup_status_pill.configure(text="● AUTO OFF", text_color=Theme.TEXT_SECONDARY)

    def _show_backup_msg(self, text: str, color: str = None, auto_clear: bool = True):
        self.backup_msg_lbl.configure(text=text, text_color=color or Theme.TEXT_SECONDARY)
        if auto_clear:
            self.after(6000, lambda: self.backup_msg_lbl.configure(text=""))

    # ================================================================== #
    #  Report Settings Card
    # ================================================================== #

    def create_report_settings_card(self):
        """📈 Report Configuration Card"""
        self.report_settings_card = ctk.CTkFrame(
            self.cards_frame,
            fg_color=Theme.BG_SECONDARY,
            corner_radius=12,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR
        )
        self.report_settings_card.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        self.report_settings_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.report_settings_card,
            text="📈 REPORT CONFIGURATION",
            font=Theme.FONT_SUBTITLE,
            text_color=Theme.TEXT_PRIMARY
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(15, 10))

        ctk.CTkLabel(self.report_settings_card, text="Export Folder", font=Theme.FONT_BODY_BOLD).grid(row=1, column=0, sticky="w", padx=20, pady=6)

        self.folder_entry_frame = ctk.CTkFrame(self.report_settings_card, fg_color="transparent")
        self.folder_entry_frame.grid(row=1, column=1, sticky="ew", padx=(10, 20), pady=6)
        self.folder_entry_frame.grid_columnconfigure(0, weight=1)

        self.export_folder_entry = ctk.CTkEntry(self.folder_entry_frame, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS)
        self.export_folder_entry.grid(row=0, column=0, sticky="ew")

        self.browse_btn = ctk.CTkButton(
            self.folder_entry_frame, text="Browse", font=Theme.FONT_CAPTION,
            width=60, fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY, command=self.browse_export_folder
        )
        self.browse_btn.grid(row=0, column=1, padx=(5, 0))

        ctk.CTkLabel(self.report_settings_card, text="PDF Name Format", font=Theme.FONT_BODY_BOLD).grid(row=2, column=0, sticky="w", padx=20, pady=6)
        self.pdf_format_entry = ctk.CTkEntry(self.report_settings_card, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS)
        self.pdf_format_entry.grid(row=2, column=1, sticky="ew", padx=(10, 20), pady=6)

        self.auto_reports_var = ctk.BooleanVar(value=True)
        self.auto_reports_sw = ctk.CTkSwitch(
            self.report_settings_card, text="Auto Generate Daily Reports",
            variable=self.auto_reports_var, font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.BORDER_COLOR, progress_color=Theme.ACCENT, command=self.save_report_settings
        )
        self.auto_reports_sw.grid(row=3, column=1, sticky="w", padx=(10, 20), pady=(8, 15))

    def create_about_card(self):
        """ℹ️ System Information (About) Card"""
        self.about_card = ctk.CTkFrame(
            self.cards_frame,
            fg_color=Theme.BG_SECONDARY,
            corner_radius=12,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR
        )
        self.about_card.grid(row=2, column=1, padx=10, pady=10, sticky="nsew")
        self.about_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.about_card,
            text="ℹ️ SYSTEM INFORMATION",
            font=Theme.FONT_SUBTITLE,
            text_color=Theme.TEXT_PRIMARY
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(15, 10))

        metrics = [
            ("Application Version", "version_lbl", "v1.1.0"),
            ("Database File Size", "db_size_lbl", "0 KB"),
            ("Active Customers", "active_cust_lbl", "0"),
            ("Logged Transactions", "logged_txns_lbl", "0")
        ]

        self.metric_labels = {}
        for idx, (label_text, var_name, default_val) in enumerate(metrics, start=1):
            ctk.CTkLabel(self.about_card, text=label_text, font=Theme.FONT_BODY_BOLD, text_color=Theme.TEXT_SECONDARY).grid(row=idx, column=0, sticky="w", padx=20, pady=5)
            lbl = ctk.CTkLabel(self.about_card, text=default_val, font=Theme.FONT_BODY_BOLD, text_color=Theme.TEXT_PRIMARY)
            lbl.grid(row=idx, column=1, sticky="e", padx=20, pady=5)
            self.metric_labels[var_name] = lbl

    def create_pdf_security_card(self):
        """🔒 PDF Security Card — password protection for all exported PDFs."""
        self.pdf_security_card = ctk.CTkFrame(
            self.cards_frame,
            fg_color=Theme.BG_SECONDARY,
            corner_radius=12,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR
        )
        self.pdf_security_card.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.pdf_security_card.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # ── Card Header row ──────────────────────────────────────────────
        header_row = ctk.CTkFrame(self.pdf_security_card, fg_color="transparent")
        header_row.grid(row=0, column=0, columnspan=4, sticky="ew", padx=20, pady=(15, 0))
        header_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header_row, text="🔒", font=(Theme.FONT_FAMILY, 22)).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkLabel(header_row, text="PDF SECURITY", font=Theme.FONT_SUBTITLE,
                     text_color=Theme.TEXT_PRIMARY, anchor="w").grid(row=0, column=1, sticky="w")

        self.pdf_sec_status_pill = ctk.CTkLabel(
            header_row, text="● DISABLED",
            font=Theme.FONT_BODY_BOLD, text_color=Theme.TEXT_SECONDARY
        )
        self.pdf_sec_status_pill.grid(row=0, column=2, sticky="e")

        # ── Separator ────────────────────────────────────────────────────
        sep = ctk.CTkFrame(self.pdf_security_card, fg_color=Theme.BORDER_COLOR, height=1)
        sep.grid(row=1, column=0, columnspan=4, sticky="ew", padx=20, pady=(10, 0))

        # ── Left column: Enable toggle + password fields ─────────────────
        left_col = ctk.CTkFrame(self.pdf_security_card, fg_color="transparent")
        left_col.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=(20, 10), pady=15)
        left_col.grid_columnconfigure(0, weight=1)

        self.pdf_sec_enabled_var = ctk.BooleanVar(value=False)
        self.pdf_sec_sw = ctk.CTkSwitch(
            left_col, text="Enable PDF Password Protection",
            variable=self.pdf_sec_enabled_var,
            font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.BORDER_COLOR, progress_color=Theme.ACCENT,
            command=self._on_pdf_security_toggle
        )
        self.pdf_sec_sw.grid(row=0, column=0, sticky="w", pady=(0, 12))

        pw_row = ctk.CTkFrame(left_col, fg_color="transparent")
        pw_row.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        pw_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(pw_row, text="Password", font=Theme.FONT_BODY_BOLD, width=100, anchor="w").grid(row=0, column=0, sticky="w")
        self.pdf_pw_entry = ctk.CTkEntry(pw_row, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS,
                                         show="●", placeholder_text="e.g. Ledger@2026")
        self.pdf_pw_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.pdf_pw_entry.bind("<KeyRelease>", self._update_strength_meter)

        cf_row = ctk.CTkFrame(left_col, fg_color="transparent")
        cf_row.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        cf_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(cf_row, text="Confirm", font=Theme.FONT_BODY_BOLD, width=100, anchor="w").grid(row=0, column=0, sticky="w")
        self.pdf_cf_entry = ctk.CTkEntry(cf_row, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS,
                                          show="●", placeholder_text="Re-enter password")
        self.pdf_cf_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        self._pdf_pw_visible = False
        self.show_pw_btn = ctk.CTkButton(
            left_col, text="👁  Show Password", font=Theme.FONT_CAPTION,
            fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_SECONDARY, width=140,
            command=self._toggle_pdf_password_visibility
        )
        self.show_pw_btn.grid(row=3, column=0, sticky="w", pady=(0, 12))

        btn_row = ctk.CTkFrame(left_col, fg_color="transparent")
        btn_row.grid(row=4, column=0, sticky="ew")

        self.save_pw_btn = ctk.CTkButton(
            btn_row, text="💾  Save Password", font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER,
            command=self._save_pdf_password
        )
        self.save_pw_btn.pack(side="left", padx=(0, 8))

        self.change_pw_btn = ctk.CTkButton(
            btn_row, text="🔄  Change Password", font=Theme.FONT_BODY_BOLD,
            fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY,
            command=self._open_change_password_dialog
        )
        self.change_pw_btn.pack(side="left")

        self.pdf_sec_msg_lbl = ctk.CTkLabel(
            left_col, text="", font=Theme.FONT_CAPTION,
            text_color=Theme.TEXT_SECONDARY, anchor="w", wraplength=380
        )
        self.pdf_sec_msg_lbl.grid(row=5, column=0, sticky="w", pady=(8, 0))

        # ── Right column: Strength meter + info panel ────────────────────
        right_col = ctk.CTkFrame(self.pdf_security_card, fg_color="transparent")
        right_col.grid(row=2, column=2, columnspan=2, sticky="nsew", padx=(10, 20), pady=15)
        right_col.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right_col, text="Password Strength", font=Theme.FONT_BODY_BOLD,
                     text_color=Theme.TEXT_SECONDARY, anchor="w").grid(row=0, column=0, sticky="w")

        meter_frame = ctk.CTkFrame(right_col, fg_color="transparent")
        meter_frame.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        for i in range(4):
            meter_frame.grid_columnconfigure(i, weight=1)

        self._strength_bars = []
        for i in range(4):
            bar = ctk.CTkProgressBar(meter_frame, height=8, corner_radius=4,
                                      mode="determinate", progress_color=Theme.BORDER_COLOR,
                                      fg_color=Theme.BG_TERTIARY)
            bar.set(1.0)
            bar.grid(row=0, column=i, sticky="ew", padx=2)
            self._strength_bars.append(bar)

        self.strength_lbl = ctk.CTkLabel(right_col, text="Enter a password above",
                                          font=Theme.FONT_CAPTION, text_color=Theme.TEXT_SECONDARY, anchor="w")
        self.strength_lbl.grid(row=2, column=0, sticky="w", pady=(4, 12))

        policy_box = ctk.CTkFrame(right_col, fg_color=Theme.BG_TERTIARY, corner_radius=8,
                                   border_width=1, border_color=Theme.BORDER_COLOR)
        policy_box.grid(row=3, column=0, sticky="nsew", pady=(0, 4))
        policy_box.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(policy_box, text="Password Policy", font=Theme.FONT_BODY_BOLD,
                     text_color=Theme.TEXT_PRIMARY, anchor="w").grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        for i, line in enumerate([
            "✔  Minimum 8 characters",
            "✔  At least one uppercase letter (A-Z)",
            "✔  At least one lowercase letter (a-z)",
            "✔  At least one number (0-9)",
            "✔  At least one special character (@, #, !...)",
            "  e.g.  Ledger@2026",
        ], start=1):
            ctk.CTkLabel(policy_box, text=line, font=Theme.FONT_CAPTION,
                         text_color=Theme.TEXT_SECONDARY, anchor="w").grid(row=i, column=0, sticky="w", padx=12, pady=1)

        ctk.CTkLabel(policy_box, text="").grid(row=7, column=0, pady=4)
        self._load_pdf_security_state()

    # ================================================================== #
    #  Common settings load/save helpers
    # ================================================================== #

    def refresh(self):
        """Called by app shell when Settings view transitions into focus."""
        self.load_settings(load_profile_entries=False)
        self.update_about_stats()
        self._refresh_backup_status()

    def update_about_stats(self):
        """Queries database stats dynamically to populate the System Info card."""
        cust_count = 0
        txn_count = 0
        db_size_str = "0 KB"

        try:
            with self.db_manager.get_connection() as conn:
                cust_count = conn.execute("SELECT COUNT(*) FROM customers;").fetchone()[0]
                txn_count = conn.execute("SELECT COUNT(*) FROM transactions;").fetchone()[0]
        except Exception as e:
            print(f"Error querying statistics: {e}")

        try:
            db_path = self.db_manager.db_path
            if os.path.exists(db_path):
                sz = os.path.getsize(db_path)
                db_size_str = f"{sz / 1024:.1f} KB" if sz < 1024 * 1024 else f"{sz / (1024 * 1024):.1f} MB"
        except Exception as e:
            print(f"Error querying database size: {e}")

        self.metric_labels["active_cust_lbl"].configure(text=str(cust_count))
        self.metric_labels["logged_txns_lbl"].configure(text=str(txn_count))
        self.metric_labels["db_size_lbl"].configure(text=db_size_str)

    def load_settings(self, load_profile_entries=False):
        """Loads business configurations from settings.json."""
        try:
            from ledger_app.services.settings_preprocessor import preprocess_settings
            preprocess_settings(SETTINGS_FILE)
        except Exception as e:
            print(f"[Settings] Preprocessor error: {e}")

        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)

                    current_theme = data.get("theme", "dark")
                    self.draw_theme_previews(current_theme)

                    if load_profile_entries:
                        self.biz_name_entry.delete(0, "end")
                        self.biz_name_entry.insert(0, data.get("name", ""))
                        self.biz_owner_entry.delete(0, "end")
                        self.biz_owner_entry.insert(0, data.get("owner_name", ""))
                        self.biz_phone_entry.delete(0, "end")
                        self.biz_phone_entry.insert(0, data.get("business_phone", ""))
                        self.biz_addr_entry.delete(0, "end")
                        self.biz_addr_entry.insert(0, data.get("address", ""))

                    self.startup_notify_var.set(data.get("startup_notification", True))
                    self.shutdown_notify_var.set(data.get("shutdown_notification", True))
                    self.daily_report_var.set(data.get("generate_daily_report", True))
                    self.wa_delivery_var.set(data.get("whatsapp_delivery", False))

                    if load_profile_entries:
                        self.export_folder_entry.delete(0, "end")
                        self.export_folder_entry.insert(0, data.get("default_export_folder", "reports"))
                        self.pdf_format_entry.delete(0, "end")
                        self.pdf_format_entry.insert(0, data.get("default_pdf_format", "Daily_Summary_{date}"))

                    self.auto_reports_var.set(data.get("auto_generate_daily_reports", True))

                    # Backup status
                    auto_enabled = data.get("auto_backup_enabled", True)
                    self.auto_backup_var.set(auto_enabled)
                    self._update_auto_backup_pill(auto_enabled)

                    last_backup = data.get("last_backup_date", "Never")
                    last_type = data.get("last_backup_type", "—")
                    self.last_backup_date_lbl.configure(text=last_backup)
                    self.last_backup_type_lbl.configure(text=last_type)

                    folder = data.get("backup_folder", "backups")
                    display_folder = folder if len(folder) <= 35 else "..." + folder[-32:]
                    self.backup_location_lbl.configure(text=display_folder)

                    # Load email recovery settings
                    self.email_recovery_var.set(data.get("email_recovery_enabled", False))

                    owner_email = ""
                    try:
                        with self.db_manager.get_connection() as conn:
                            row = conn.execute("SELECT recovery_email FROM users WHERE role = 'owner' LIMIT 1;").fetchone()
                            if row:
                                owner_email = row["recovery_email"] or ""
                    except Exception as e:
                        print(f"Error loading owner email: {e}")
                    self.owner_email_entry.delete(0, "end")
                    self.owner_email_entry.insert(0, owner_email)

            except Exception as e:
                print(f"Error loading settings: {e}")
        else:
            self.draw_theme_previews("dark")

    def create_email_settings_card(self):
        """📧 Email Recovery Settings Card"""
        self.email_card = ctk.CTkFrame(
            self.cards_frame,
            fg_color=Theme.BG_SECONDARY,
            corner_radius=12,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR
        )
        self.email_card.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="new")
        self.email_card.grid_columnconfigure((0, 1), weight=1)

        # Header
        hdr = ctk.CTkFrame(self.email_card, fg_color="transparent")
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(15, 10))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text="📧", font=(Theme.FONT_FAMILY, 20)).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkLabel(
            hdr, text="EMAIL RECOVERY SETTINGS",
            font=Theme.FONT_SUBTITLE,
            text_color=Theme.TEXT_PRIMARY,
            anchor="w"
        ).grid(row=0, column=1, sticky="w")

        # Separator
        ctk.CTkFrame(self.email_card, fg_color=Theme.BORDER_COLOR, height=1).grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 10)
        )

        # Content frame
        form = ctk.CTkFrame(self.email_card, fg_color="transparent")
        form.grid(row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=5)
        form.grid_columnconfigure(1, weight=1)

        # Email Recovery Switch
        self.email_recovery_var = ctk.BooleanVar(value=False)
        self.email_recovery_sw = ctk.CTkSwitch(
            form, text="Enable Email Recovery",
            variable=self.email_recovery_var, font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.BORDER_COLOR, progress_color=Theme.ACCENT
        )
        self.email_recovery_sw.grid(row=0, column=0, columnspan=2, sticky="w", pady=6)

        # Owner Email
        ctk.CTkLabel(form, text="Owner Recovery Email", font=Theme.FONT_BODY_BOLD).grid(row=1, column=0, sticky="w", pady=6)
        self.owner_email_entry = ctk.CTkEntry(form, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS, placeholder_text="owner@example.com")
        self.owner_email_entry.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=6)

        # Button Row
        btn_row = ctk.CTkFrame(self.email_card, fg_color="transparent")
        btn_row.grid(row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=(10, 15))
        btn_row.grid_columnconfigure((0, 1), weight=1)

        self.test_email_btn = ctk.CTkButton(
            btn_row, text="📧 Test Email Connection", font=Theme.FONT_BODY_BOLD,
            fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY, command=self.test_email_settings
        )
        self.test_email_btn.grid(row=0, column=0, padx=(0, 5), pady=4, sticky="ew")

        self.save_email_btn = ctk.CTkButton(
            btn_row, text="Save Settings", font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER, command=self.save_email_settings
        )
        self.save_email_btn.grid(row=0, column=1, padx=(5, 0), pady=4, sticky="ew")

    def save_email_settings(self):
        recovery_enabled = self.email_recovery_var.get()
        owner_email = self.owner_email_entry.get().strip()

        if recovery_enabled:
            if not owner_email or "@" not in owner_email:
                messagebox.showerror("Error", "Please configure a valid Owner Recovery Email.")
                return

        try:
            with self.db_manager.get_connection() as conn:
                row = conn.execute("SELECT id FROM users WHERE role = 'owner' LIMIT 1;").fetchone()
                if row:
                    conn.execute("UPDATE users SET recovery_email = ? WHERE id = ?;", (owner_email, row["id"]))
                else:
                    messagebox.showerror("Error", "Owner account not found in database.")
                    return
        except Exception as e:
            messagebox.showerror("Error Saving Recovery Email", f"Could not update database: {e}")
            return

        data = {}
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
            except Exception:
                pass

        data["email_recovery_enabled"] = recovery_enabled

        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=4)
            
            try:
                with self.db_manager.get_connection() as conn:
                    conn.execute(
                        "INSERT INTO audit_logs (username, action, details) VALUES (?, ?, ?);",
                        ("owner", "SETTINGS_MODIFIED", "Email recovery settings updated.")
                    )
            except Exception:
                pass
                
            messagebox.showinfo("Settings Saved", "Email recovery configuration saved successfully!")
        except Exception as e:
            messagebox.showerror("Error Saving Settings", f"Could not write configuration: {e}")

    def test_email_settings(self):
        owner_email = self.owner_email_entry.get().strip()

        if not owner_email or "@" not in owner_email:
            messagebox.showerror("Error", "Please enter a valid Owner Recovery Email to receive the test mail.")
            return

        try:
            from ledger_app.services.settings_preprocessor import preprocess_settings
            preprocess_settings(SETTINGS_FILE)
        except Exception as e:
            print(f"[Settings] Preprocessor error in test: {e}")

        data = {}
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
            except Exception:
                pass

        sender_email = data.get("sender_email")
        sender_pw = data.get("sender_password") or data.get("sender_password_obfuscated")
        if not sender_email or not sender_pw:
            messagebox.showerror("Error", "No SMTP sender credentials configured in settings.json. Please set 'sender_email' and 'sender_password' directly in settings.json.")
            return

        self.test_email_btn.configure(state="disabled", text="⏳ Sending test email...")
        self.update()

        import threading
        
        def run_test():
            success = False
            error_msg = ""
            try:
                from ledger_app.services.email_service import EmailService
                test_svc = EmailService()
                success = test_svc.send_email_report(
                    subject="Jalaj Ledger - SMTP Test Email",
                    body="Congratulations! Your SMTP connection and credentials configured in settings.json are working.",
                    recipient_override=owner_email
                )
            except Exception as e:
                error_msg = str(e)
                
            def done():
                self.test_email_btn.configure(state="normal", text="📧 Test Email Connection")
                if success:
                    messagebox.showinfo("Success", f"Test email sent successfully to {owner_email}!")
                else:
                    messagebox.showerror("SMTP Error", f"Failed to send test email.\nDetails: {error_msg or 'Check credentials and SMTP settings.'}")
                    
            self.after(0, done)

        threading.Thread(target=run_test, daemon=True).start()

    def change_theme(self, theme_name: str):
        ThemeManager.set_theme(theme_name)
        self.draw_theme_previews(theme_name)

    def save_profile(self):
        data = {}
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
            except Exception:
                pass
        data.update({
            "name": self.biz_name_entry.get().strip(),
            "owner_name": self.biz_owner_entry.get().strip(),
            "business_phone": self.biz_phone_entry.get().strip(),
            "address": self.biz_addr_entry.get().strip()
        })
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=4)
            messagebox.showinfo("Profile Saved", "Business profile saved successfully!")
        except Exception as e:
            messagebox.showerror("Error Saving Settings", f"Could not write configuration: {e}")

    def save_notifications(self):
        data = {}
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
            except Exception:
                pass
        data.update({
            "startup_notification": self.startup_notify_var.get(),
            "shutdown_notification": self.shutdown_notify_var.get(),
            "generate_daily_report": self.daily_report_var.get(),
            "whatsapp_delivery": self.wa_delivery_var.get()
        })
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving notification configurations: {e}")

    def save_report_settings(self):
        data = {}
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
            except Exception:
                pass
        data.update({
            "default_export_folder": self.export_folder_entry.get().strip(),
            "default_pdf_format": self.pdf_format_entry.get().strip(),
            "auto_generate_daily_reports": self.auto_reports_var.get()
        })
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving report settings: {e}")

    def browse_export_folder(self):
        folder = filedialog.askdirectory(title="Select Default Exports Folder")
        if folder:
            self.export_folder_entry.delete(0, "end")
            self.export_folder_entry.insert(0, folder)
            self.save_report_settings()

    # ================================================================== #
    #  PDF Security Card — Event Handlers (preserved exactly)
    # ================================================================== #

    def _load_pdf_security_state(self):
        try:
            sec = PdfSecurityService.load_pdf_security_settings()
            enabled = sec.get("pdf_security_enabled", False)
            has_hash = bool(sec.get("password_hash", ""))
            self.pdf_sec_enabled_var.set(enabled)
            self._refresh_status_pill(enabled, has_hash)
        except Exception as e:
            print(f"[Settings] Error loading PDF security state: {e}")

    def _refresh_status_pill(self, enabled: bool, has_password: bool):
        if enabled and has_password:
            self.pdf_sec_status_pill.configure(text="● PROTECTED", text_color="#22C55E")
        elif enabled and not has_password:
            self.pdf_sec_status_pill.configure(text="● NO PASSWORD SET", text_color="#F59E0B")
        else:
            self.pdf_sec_status_pill.configure(text="● DISABLED", text_color=Theme.TEXT_SECONDARY)

    def _on_pdf_security_toggle(self):
        enabled = self.pdf_sec_enabled_var.get()
        try:
            PdfSecurityService.set_enabled(enabled)
            sec = PdfSecurityService.load_pdf_security_settings()
            has_hash = bool(sec.get("password_hash", ""))
            self._refresh_status_pill(enabled, has_hash)
            if enabled and not has_hash:
                self._show_pdf_msg("⚠  Security enabled — please set a password below and click Save Password.", color="#F59E0B")
            elif enabled:
                self._show_pdf_msg("✔  PDF password protection is now active.", color="#22C55E")
            else:
                self._show_pdf_msg("PDF password protection disabled.", color=Theme.TEXT_SECONDARY)
        except Exception as e:
            self._show_pdf_msg(f"Error saving toggle: {e}", color="#EF4444")

    def _update_strength_meter(self, event=None):
        password = self.pdf_pw_entry.get()
        score = PdfSecurityService.get_password_strength_score(password)
        colours = ["#EF4444", "#F97316", "#EAB308", "#22C55E"]
        labels = ["Very Weak", "Weak", "Fair", "Strong", "Very Strong"]
        active_colour = colours[min(score, 3)] if score > 0 else Theme.BORDER_COLOR
        for i, bar in enumerate(self._strength_bars):
            bar.configure(progress_color=active_colour if i < score else Theme.BORDER_COLOR)
        if not password:
            self.strength_lbl.configure(text="Enter a password above", text_color=Theme.TEXT_SECONDARY)
        else:
            self.strength_lbl.configure(text=f"Strength: {labels[score]}", text_color=active_colour)

    def _toggle_pdf_password_visibility(self):
        self._pdf_pw_visible = not self._pdf_pw_visible
        char = "" if self._pdf_pw_visible else "●"
        self.pdf_pw_entry.configure(show=char)
        self.pdf_cf_entry.configure(show=char)
        self.show_pw_btn.configure(text="🙈  Hide Password" if self._pdf_pw_visible else "👁  Show Password")

    def _show_pdf_msg(self, text: str, color: str = None, auto_clear: bool = True):
        self.pdf_sec_msg_lbl.configure(text=text, text_color=color or Theme.TEXT_SECONDARY)
        if auto_clear:
            self.after(5000, lambda: self.pdf_sec_msg_lbl.configure(text=""))

    def _save_pdf_password(self):
        password = self.pdf_pw_entry.get()
        confirm = self.pdf_cf_entry.get()
        ok, reason = PdfSecurityService.validate_password_strength(password)
        if not ok:
            self._show_pdf_msg(f"❌  {reason}", color="#EF4444")
            return
        if password != confirm:
            self._show_pdf_msg("❌  Passwords do not match. Please re-enter both fields.", color="#EF4444")
            return
        try:
            salt_hex, hash_hex = PdfSecurityService.hash_password(password)
            enabled = self.pdf_sec_enabled_var.get()
            PdfSecurityService.save_pdf_security_settings(
                enabled=enabled, password_hash=hash_hex, salt=salt_hex, raw_password=password
            )
            self.pdf_pw_entry.delete(0, "end")
            self.pdf_cf_entry.delete(0, "end")
            self._update_strength_meter()
            self._refresh_status_pill(enabled, True)
            self._show_pdf_msg("✔  Password saved successfully. All future PDF exports will be encrypted.", color="#22C55E")
        except Exception as e:
            self._show_pdf_msg(f"❌  Failed to save password: {e}", color="#EF4444")

    def _open_change_password_dialog(self):
        sec = PdfSecurityService.load_pdf_security_settings()
        if not sec.get("password_hash"):
            self._show_pdf_msg("⚠  No password is set yet. Use 'Save Password' to set one first.", color="#F59E0B")
            return
        PasswordChangeDialog(self, on_success=self._on_password_changed)

    def _on_password_changed(self):
        self._load_pdf_security_state()
        self._show_pdf_msg("✔  Password changed successfully. New password will apply to all future exports.", color="#22C55E")


# ====================================================================== #
#  Backup History Dialog
# ====================================================================== #

class BackupHistoryDialog(ctk.CTkToplevel):
    """
    Modal dialog showing the full backup history with options to restore or delete each entry.
    """

    COL_WIDTHS = [300, 140, 80, 100, 160]  # File, Date, Size, Type, Actions
    COL_HEADERS = ["File Name", "Created Date", "Size", "Type", "Actions"]

    def __init__(self, parent, backup_manager, on_restore_request=None):
        super().__init__(parent)
        self.backup_manager = backup_manager
        self.on_restore_request = on_restore_request

        self.title("Backup History")
        width, height = 900, 520
        px = parent.winfo_x() + max(0, (parent.winfo_width() - width) // 2)
        py = parent.winfo_y() + max(0, (parent.winfo_height() - height) // 2)
        self.geometry(f"{width}x{height}+{px}+{py}")
        self.resizable(True, True)
        self.configure(fg_color=Theme.BG_SECONDARY)
        self.transient(parent)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Header ────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 8))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text="📋  Backup History",
                     font=Theme.FONT_SUBTITLE, text_color=Theme.TEXT_PRIMARY).grid(row=0, column=0, sticky="w")

        self.count_lbl = ctk.CTkLabel(hdr, text="", font=Theme.FONT_CAPTION,
                                       text_color=Theme.TEXT_SECONDARY)
        self.count_lbl.grid(row=0, column=1, sticky="e")

        ctk.CTkButton(hdr, text="✕", width=32, height=28, font=Theme.FONT_BODY_BOLD,
                      fg_color="transparent", hover_color=Theme.BG_TERTIARY,
                      text_color=Theme.TEXT_PRIMARY, command=self.destroy
                      ).grid(row=0, column=2, sticky="e", padx=(8, 0))

        # ── Separator ─────────────────────────────────────────────────────
        ctk.CTkFrame(self, fg_color=Theme.BORDER_COLOR, height=1).grid(
            row=1, column=0, sticky="ew", padx=20, pady=0
        )

        # ── Column headers ────────────────────────────────────────────────
        hdr_row = ctk.CTkFrame(self, fg_color=Theme.BG_TERTIARY, height=34, corner_radius=0)
        hdr_row.grid(row=2, column=0, sticky="ew", padx=20, pady=(6, 0))
        hdr_row.grid_propagate(False)
        for i, (h, w) in enumerate(zip(self.COL_HEADERS, self.COL_WIDTHS)):
            hdr_row.grid_columnconfigure(i, minsize=w, weight=1 if i == 0 else 0)
            anchor = "w" if i == 0 else "center"
            ctk.CTkLabel(hdr_row, text=h.upper(), font=Theme.FONT_CAPTION,
                         text_color=Theme.TEXT_SECONDARY, anchor=anchor
                         ).grid(row=0, column=i, sticky="nsew", padx=8, pady=6)

        # ── Scrollable list ───────────────────────────────────────────────
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self.scroll.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 4))
        self.grid_rowconfigure(3, weight=1)
        for i, w in enumerate(self.COL_WIDTHS):
            self.scroll.grid_columnconfigure(i, minsize=w, weight=1 if i == 0 else 0)

        # ── Footer ────────────────────────────────────────────────────────
        ctk.CTkFrame(self, fg_color=Theme.BORDER_COLOR, height=1).grid(
            row=4, column=0, sticky="ew", padx=20
        )
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=5, column=0, sticky="ew", padx=20, pady=(8, 16))

        self.status_lbl = ctk.CTkLabel(footer, text="", font=Theme.FONT_CAPTION,
                                        text_color=Theme.TEXT_SECONDARY, anchor="w")
        self.status_lbl.pack(side="left")

        ctk.CTkButton(footer, text="Close", width=90, font=Theme.FONT_BODY_BOLD,
                      fg_color="transparent", hover_color=Theme.BG_TERTIARY,
                      border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR,
                      text_color=Theme.TEXT_PRIMARY, command=self.destroy
                      ).pack(side="right")

        self._load_history()

    def _load_history(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        history = self.backup_manager.get_backup_history()
        self.count_lbl.configure(text=f"{len(history)} backup(s) found")

        if not history:
            ctk.CTkLabel(self.scroll, text="No backups found.",
                         font=Theme.FONT_BODY, text_color=Theme.TEXT_SECONDARY
                         ).grid(row=0, column=0, columnspan=5, pady=40)
            return

        type_colors = {
            "Manual":      "#14B8A6",
            "Automatic":   "#0EA5E9",
            "Shutdown":    "#8B5CF6",
            "Pre-Restore": "#F59E0B",
            "Pre-Delete":  "#EF4444",
        }

        for idx, b in enumerate(history):
            bg = Theme.BG_SECONDARY if idx % 2 == 0 else Theme.BG_TERTIARY

            row_data = [
                b.file_name,
                b.created_at.strftime("%Y-%m-%d  %H:%M"),
                b.size_str,
                b.backup_type,
            ]
            for col, (text, min_w) in enumerate(zip(row_data, self.COL_WIDTHS)):
                cell = ctk.CTkFrame(self.scroll, fg_color=bg, corner_radius=0)
                cell.grid(row=idx, column=col, sticky="nsew", ipady=6)
                anchor = "w" if col == 0 else "center"

                if col == 3:  # Type badge
                    badge_color = type_colors.get(text, Theme.TEXT_SECONDARY)
                    ctk.CTkLabel(cell, text=text, font=Theme.FONT_CAPTION,
                                 text_color=badge_color, anchor="center",
                                 ).pack(expand=True)
                else:
                    ctk.CTkLabel(cell, text=text, font=Theme.FONT_CAPTION,
                                 text_color=Theme.TEXT_PRIMARY, anchor=anchor
                                 ).pack(side="left", padx=(10 if col == 0 else 4, 4), expand=(col == 0), fill="x")

            # Actions column
            act_cell = ctk.CTkFrame(self.scroll, fg_color=bg, corner_radius=0)
            act_cell.grid(row=idx, column=4, sticky="nsew", ipady=4)

            btn_box = ctk.CTkFrame(act_cell, fg_color="transparent")
            btn_box.pack(anchor="center")

            ctk.CTkButton(
                btn_box, text="Restore", width=62, height=24, font=Theme.FONT_CAPTION,
                fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER,
                command=lambda path=b.file_path: self._on_restore(path)
            ).pack(side="left", padx=2)

            ctk.CTkButton(
                btn_box, text="Delete", width=55, height=24, font=Theme.FONT_CAPTION,
                fg_color="transparent", hover_color=Theme.DANGER_HOVER,
                border_width=Theme.BORDER_WIDTH, border_color=Theme.DEBIT_RED,
                text_color=Theme.DEBIT_RED,
                command=lambda path=b.file_path, name=b.file_name: self._on_delete(path, name)
            ).pack(side="left", padx=2)

    def _on_restore(self, zip_path: str):
        self.destroy()
        if self.on_restore_request:
            self.on_restore_request(zip_path)

    def _on_delete(self, zip_path: str, file_name: str):
        if not messagebox.askyesno("Confirm Delete",
                                   f"Permanently delete this backup?\n\n{file_name}",
                                   icon="warning"):
            return
        try:
            os.remove(zip_path)
            self.status_lbl.configure(text=f"✔  Deleted: {file_name}", text_color="#22C55E")
            self._load_history()
        except Exception as e:
            messagebox.showerror("Delete Failed", f"Could not delete backup:\n{e}")


# ====================================================================== #
#  Backup Restore Dialog
# ====================================================================== #

class BackupRestoreDialog(ctk.CTkToplevel):
    """
    Guided restore dialog.
    Shows backup list, preview panel, and confirms before applying restore.
    """

    def __init__(self, parent, backup_manager, db_path, on_restore_complete=None, preselected_zip=None):
        super().__init__(parent)
        self.backup_manager = backup_manager
        self.db_path = db_path
        self.on_restore_complete = on_restore_complete
        self._selected_zip = preselected_zip
        self._history = []

        self.title("Restore Backup")
        width, height = 860, 580
        px = parent.winfo_x() + max(0, (parent.winfo_width() - width) // 2)
        py = parent.winfo_y() + max(0, (parent.winfo_height() - height) // 2)
        self.geometry(f"{width}x{height}+{px}+{py}")
        self.resizable(True, True)
        self.configure(fg_color=Theme.BG_SECONDARY)
        self.transient(parent)
        self.grab_set()
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        # ── Header ────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(20, 0))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text="🔄  Restore Backup",
                     font=Theme.FONT_SUBTITLE, text_color=Theme.TEXT_PRIMARY).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(hdr, text="Select a backup from the list, then click Restore.",
                     font=Theme.FONT_CAPTION, text_color=Theme.TEXT_SECONDARY).grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 0))

        # ── Left: backup list ─────────────────────────────────────────────
        list_frame = ctk.CTkFrame(self, fg_color=Theme.BG_TERTIARY, corner_radius=8,
                                   border_width=1, border_color=Theme.BORDER_COLOR)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=(20, 6), pady=15)
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(list_frame, text="AVAILABLE BACKUPS", font=Theme.FONT_CAPTION,
                     text_color=Theme.TEXT_SECONDARY, anchor="w"
                     ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        self.list_scroll = ctk.CTkScrollableFrame(list_frame, fg_color="transparent")
        self.list_scroll.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 8))
        self.list_scroll.grid_columnconfigure(0, weight=1)

        # ── Right: preview panel ──────────────────────────────────────────
        preview_frame = ctk.CTkFrame(self, fg_color=Theme.BG_TERTIARY, corner_radius=8,
                                      border_width=1, border_color=Theme.BORDER_COLOR)
        preview_frame.grid(row=1, column=1, sticky="nsew", padx=(6, 20), pady=15)
        preview_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(preview_frame, text="BACKUP PREVIEW", font=Theme.FONT_CAPTION,
                     text_color=Theme.TEXT_SECONDARY, anchor="w"
                     ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        ctk.CTkFrame(preview_frame, fg_color=Theme.BORDER_COLOR, height=1).grid(
            row=1, column=0, sticky="ew", padx=12, pady=0
        )

        self._preview_labels = {}
        preview_fields = [
            ("Type", "type"),
            ("Created", "created"),
            ("App Version", "version"),
            ("Size", "size"),
            ("Files Included", "files"),
        ]
        for i, (label, key) in enumerate(preview_fields, start=2):
            ctk.CTkLabel(preview_frame, text=label, font=Theme.FONT_BODY_BOLD,
                         text_color=Theme.TEXT_SECONDARY, anchor="w"
                         ).grid(row=i, column=0, sticky="w", padx=12, pady=(8, 0))
            val_lbl = ctk.CTkLabel(preview_frame, text="—", font=Theme.FONT_BODY,
                                    text_color=Theme.TEXT_PRIMARY, anchor="w",
                                    wraplength=200, justify="left")
            val_lbl.grid(row=i + len(preview_fields), column=0, sticky="w", padx=20, pady=(0, 4))
            self._preview_labels[key] = val_lbl

        # Warning box
        warn_box = ctk.CTkFrame(preview_frame, fg_color=Theme.BG_SECONDARY, corner_radius=6,
                                 border_width=1, border_color=Theme.WARNING_ORANGE)
        warn_box.grid(row=99, column=0, sticky="ew", padx=12, pady=(12, 4))
        ctk.CTkLabel(warn_box,
                     text="⚠  A safety backup will be\ncreated before restoring.",
                     font=Theme.FONT_CAPTION, text_color=Theme.WARNING_ORANGE,
                     justify="left", anchor="w"
                     ).pack(padx=10, pady=8, anchor="w")

        # ── Footer ────────────────────────────────────────────────────────
        ctk.CTkFrame(self, fg_color=Theme.BORDER_COLOR, height=1).grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=0
        )
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=(10, 16))
        footer.grid_columnconfigure(1, weight=1)

        self.progress_lbl = ctk.CTkLabel(footer, text="", font=Theme.FONT_CAPTION,
                                          text_color=Theme.TEXT_SECONDARY, anchor="w")
        self.progress_lbl.grid(row=0, column=0, sticky="w")

        btn_frame = ctk.CTkFrame(footer, fg_color="transparent")
        btn_frame.grid(row=0, column=1, sticky="e")

        ctk.CTkButton(btn_frame, text="Cancel", width=90, font=Theme.FONT_BODY_BOLD,
                      fg_color="transparent", hover_color=Theme.BG_TERTIARY,
                      border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR,
                      text_color=Theme.TEXT_PRIMARY, command=self.destroy
                      ).pack(side="left", padx=(0, 8))

        self.restore_btn = ctk.CTkButton(
            btn_frame, text="🔄  Restore Selected", width=160, font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER,
            state="disabled", command=self._do_restore
        )
        self.restore_btn.pack(side="left")

        self._load_list()

        # Auto-select preselected zip if provided
        if self._selected_zip:
            self._select_zip(self._selected_zip)

    def _load_list(self):
        for w in self.list_scroll.winfo_children():
            w.destroy()

        self._history = self.backup_manager.get_backup_history()
        if not self._history:
            ctk.CTkLabel(self.list_scroll, text="No backups found.",
                         font=Theme.FONT_BODY, text_color=Theme.TEXT_SECONDARY
                         ).pack(pady=30)
            return

        self._row_frames = []
        for b in self._history:
            row = ctk.CTkFrame(self.list_scroll, fg_color="transparent", corner_radius=6,
                                cursor="hand2")
            row.pack(fill="x", pady=2, padx=4)
            row.grid_columnconfigure(0, weight=1)

            inner = ctk.CTkFrame(row, fg_color=Theme.BG_SECONDARY, corner_radius=6,
                                  border_width=1, border_color=Theme.BORDER_COLOR)
            inner.pack(fill="x")

            ctk.CTkLabel(inner, text=b.file_name, font=Theme.FONT_CAPTION,
                         text_color=Theme.TEXT_PRIMARY, anchor="w",
                         wraplength=300
                         ).pack(anchor="w", padx=10, pady=(6, 2))

            meta_row = ctk.CTkFrame(inner, fg_color="transparent")
            meta_row.pack(anchor="w", padx=10, pady=(0, 6))
            ctk.CTkLabel(meta_row,
                         text=f"{b.created_at.strftime('%Y-%m-%d %H:%M')}  •  {b.size_str}  •  {b.backup_type}",
                         font=Theme.FONT_CAPTION, text_color=Theme.TEXT_SECONDARY).pack(side="left")

            inner.bind("<Button-1>", lambda e, path=b.file_path, frm=inner: self._on_row_click(path, frm))
            for child in inner.winfo_children():
                child.bind("<Button-1>", lambda e, path=b.file_path, frm=inner: self._on_row_click(path, frm))

            self._row_frames.append((b.file_path, inner))

    def _on_row_click(self, zip_path: str, frame):
        self._select_zip(zip_path)
        # Highlight selected row
        for path, frm in self._row_frames:
            frm.configure(border_color=Theme.ACCENT if path == zip_path else Theme.BORDER_COLOR)

    def _select_zip(self, zip_path: str):
        self._selected_zip = zip_path
        self.restore_btn.configure(state="normal")
        self._update_preview(zip_path)

    def _update_preview(self, zip_path: str):
        from ledger_app.services.restore_service import RestoreService
        preview = RestoreService.get_restore_preview(zip_path)

        if not preview.get("valid"):
            self.progress_lbl.configure(text=f"⚠  {preview.get('error', 'Invalid backup')}", text_color="#EF4444")
            self.restore_btn.configure(state="disabled")
            return

        self._preview_labels["type"].configure(text=preview.get("backup_type", "—"))
        self._preview_labels["created"].configure(text=preview.get("created_at", "—"))
        self._preview_labels["version"].configure(text=preview.get("app_version", "—"))
        self._preview_labels["size"].configure(text=preview.get("size_str", "—"))
        files = preview.get("files_included", [])
        self._preview_labels["files"].configure(text="\n".join(files) if files else "—")

    def _do_restore(self):
        if not self._selected_zip:
            return

        confirm = messagebox.askyesno(
            "Confirm Restore",
            "Are you sure you want to restore this backup?\n\n"
            "• A safety backup will be created first\n"
            "• Current database and settings will be overwritten\n"
            "• Application restart is recommended after restore",
            icon="warning"
        )
        if not confirm:
            return

        self.restore_btn.configure(state="disabled", text="⏳  Restoring...")
        self.progress_lbl.configure(text="Creating safety backup and restoring...", text_color=Theme.TEXT_SECONDARY)
        self.update()

        from ledger_app.services.restore_service import RestoreService
        backup_dir = self.backup_manager.get_backup_dir()
        success, message = RestoreService.restore_backup(
            zip_path      = self._selected_zip,
            db_path       = self.db_path,
            settings_file = SETTINGS_FILE,
            backup_dir    = backup_dir,
        )

        if success:
            self.restore_btn.configure(text="✔  Restored")
            self.progress_lbl.configure(text="✔  Restore successful!", text_color="#22C55E")
            messagebox.showinfo(
                "Restore Completed",
                f"{message}\n\nPlease restart the application to ensure all data is loaded correctly."
            )
            self.destroy()
            if self.on_restore_complete:
                self.on_restore_complete(True, message)
        else:
            self.restore_btn.configure(state="normal", text="🔄  Restore Selected")
            self.progress_lbl.configure(text=f"❌  {message}", text_color="#EF4444")
            messagebox.showerror("Restore Failed", message)
            if self.on_restore_complete:
                self.on_restore_complete(False, message)


# ====================================================================== #
#  Password Change Dialog (preserved exactly)
# ====================================================================== #

class PasswordChangeDialog(ctk.CTkToplevel):
    """
    Modal dialog for securely changing the PDF protection password.
    Requires the current password to be verified before accepting the new one.
    """

    def __init__(self, parent, on_success: callable):
        super().__init__(parent)
        self.on_success = on_success

        self.title("Change PDF Password")
        width, height = 420, 400
        parent_top = parent.winfo_toplevel()
        x = parent_top.winfo_x() + (parent_top.winfo_width()  - width)  // 2
        y = parent_top.winfo_y() + (parent_top.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.resizable(False, False)
        self.configure(fg_color=Theme.BG_SECONDARY)
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="🔄  Change PDF Password",
                     font=Theme.FONT_SUBTITLE, text_color=Theme.TEXT_PRIMARY
                     ).grid(row=0, column=0, padx=24, pady=(20, 4), sticky="w")

        ctk.CTkLabel(self, text="Verify your current password, then enter a new one.",
                     font=Theme.FONT_CAPTION, text_color=Theme.TEXT_SECONDARY
                     ).grid(row=1, column=0, padx=24, pady=(0, 12), sticky="w")

        sep = ctk.CTkFrame(self, fg_color=Theme.BORDER_COLOR, height=1)
        sep.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 16))

        fields_frame = ctk.CTkFrame(self, fg_color="transparent")
        fields_frame.grid(row=3, column=0, sticky="ew", padx=24)
        fields_frame.grid_columnconfigure(1, weight=1)

        labels = ["Current Password", "New Password", "Confirm New"]
        self._entries = {}
        for i, lbl_text in enumerate(labels):
            ctk.CTkLabel(fields_frame, text=lbl_text, font=Theme.FONT_BODY_BOLD,
                         anchor="w", width=130).grid(row=i, column=0, sticky="w", pady=7)
            entry = ctk.CTkEntry(fields_frame, font=Theme.FONT_BODY,
                                  corner_radius=Theme.CORNER_RADIUS, show="●",
                                  placeholder_text="••••••••")
            entry.grid(row=i, column=1, sticky="ew", padx=(8, 0), pady=7)
            self._entries[lbl_text] = entry

        self._entries["New Password"].bind("<KeyRelease>", self._on_new_pw_key)

        self.dlg_strength_lbl = ctk.CTkLabel(self, text="", font=Theme.FONT_CAPTION,
                                              text_color=Theme.TEXT_SECONDARY, anchor="w")
        self.dlg_strength_lbl.grid(row=4, column=0, sticky="w", padx=24, pady=(4, 0))

        self.dlg_msg_lbl = ctk.CTkLabel(self, text="", font=Theme.FONT_CAPTION,
                                         text_color="#EF4444", anchor="w", wraplength=370)
        self.dlg_msg_lbl.grid(row=5, column=0, sticky="w", padx=24, pady=(6, 0))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=6, column=0, sticky="ew", padx=24, pady=(16, 20))

        ctk.CTkButton(btn_row, text="Cancel", font=Theme.FONT_BODY_BOLD,
                      fg_color="transparent", hover_color=Theme.BG_TERTIARY,
                      border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR,
                      text_color=Theme.TEXT_PRIMARY, width=110, command=self.destroy
                      ).pack(side="left")

        ctk.CTkButton(btn_row, text="✔  Update Password", font=Theme.FONT_BODY_BOLD,
                      fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER,
                      width=160, command=self._do_change
                      ).pack(side="right")

    def _on_new_pw_key(self, event=None):
        pw = self._entries["New Password"].get()
        score = PdfSecurityService.get_password_strength_score(pw)
        labels = ["", "Very Weak", "Weak", "Fair", "Strong", "Very Strong"]
        colours = ["", "#EF4444", "#F97316", "#EAB308", "#22C55E", "#22C55E"]
        if pw:
            self.dlg_strength_lbl.configure(text=f"Strength: {labels[score]}", text_color=colours[score])
        else:
            self.dlg_strength_lbl.configure(text="")

    def _do_change(self):
        current_pw = self._entries["Current Password"].get()
        new_pw     = self._entries["New Password"].get()
        confirm_pw = self._entries["Confirm New"].get()

        sec = PdfSecurityService.load_pdf_security_settings()
        stored_hash = sec.get("password_hash", "")
        stored_salt = sec.get("salt", "")

        if not stored_hash or not stored_salt:
            self.dlg_msg_lbl.configure(text="❌  No existing password found. Use Save Password instead.")
            return

        if not PdfSecurityService.verify_password(current_pw, stored_hash, stored_salt):
            self.dlg_msg_lbl.configure(text="❌  Current password is incorrect.")
            return

        ok, reason = PdfSecurityService.validate_password_strength(new_pw)
        if not ok:
            self.dlg_msg_lbl.configure(text=f"❌  {reason}")
            return

        if new_pw != confirm_pw:
            self.dlg_msg_lbl.configure(text="❌  New passwords do not match.")
            return

        try:
            new_salt, new_hash = PdfSecurityService.hash_password(new_pw)
            PdfSecurityService.save_pdf_security_settings(
                enabled=sec.get("pdf_security_enabled", True),
                password_hash=new_hash,
                salt=new_salt,
                raw_password=new_pw
            )
            self.destroy()
            if callable(self.on_success):
                self.on_success()
        except Exception as e:
            self.dlg_msg_lbl.configure(text=f"❌  Failed to save: {e}")




        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. Header Frame Row
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        
        self.title_lbl = ctk.CTkLabel(
            self.header_frame, 
            text="Settings & Preferences", 
            font=Theme.FONT_TITLE, 
            text_color=Theme.TEXT_PRIMARY,
            anchor="w"
        )
        self.title_lbl.pack(side="left")

        # Scrollable grid container for 6 settings cards
        self.cards_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.cards_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        self.cards_frame.grid_columnconfigure((0, 1), weight=1, uniform="settings_cols")

        # Create the 6 Settings Cards + 1 Security Card
        self.create_theme_card()
        self.create_profile_card()
        self.create_notifications_card()
        self.create_backup_card()
        self.create_report_settings_card()
        self.create_about_card()
        self.create_pdf_security_card()

        # Load values into UI
        self.load_settings(load_profile_entries=True)
        self.update_about_stats()

    def create_theme_card(self):
        """🎨 Theme Selection Card"""
        self.theme_card = ctk.CTkFrame(
            self.cards_frame, 
            fg_color=Theme.BG_SECONDARY, 
            corner_radius=12,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR
        )
        self.theme_card.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.theme_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.theme_card, 
            text="🎨 THEME SELECTION", 
            font=Theme.FONT_SUBTITLE,
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w", padx=20, pady=(15, 10))
        
        self.theme_previews_box = ctk.CTkFrame(self.theme_card, fg_color="transparent")
        self.theme_previews_box.pack(fill="x", padx=20, pady=(0, 15))
        self.theme_previews_box.grid_columnconfigure((0, 1), weight=1)

    def draw_theme_previews(self, current_theme: str):
        """Re-draws Light & Dark mode visual preview cards based on selection state."""
        for widget in self.theme_previews_box.winfo_children():
            widget.destroy()

        # Light Preview
        light_preview = ThemePreviewCard(
            self.theme_previews_box,
            theme_name="Light Mode",
            bg_color="#F8FAFC",
            sidebar_color="#FFFFFF",
            card_color="#FFFFFF",
            accent_color="#0EA5E9",
            border_color="#E2E8F0",
            text_color="#0F172A",
            is_selected=(current_theme == "light"),
            command=lambda: self.change_theme("light")
        )
        light_preview.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # Dark Preview
        dark_preview = ThemePreviewCard(
            self.theme_previews_box,
            theme_name="Dark Mode",
            bg_color="#0B1220",
            sidebar_color="#111827",
            card_color="#1E293B",
            accent_color="#14B8A6",
            border_color="#334155",
            text_color="#F8FAFC",
            is_selected=(current_theme == "dark"),
            command=lambda: self.change_theme("dark")
        )
        dark_preview.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

    def create_profile_card(self):
        """💼 Business Profile Card"""
        self.profile_card = ctk.CTkFrame(
            self.cards_frame, 
            fg_color=Theme.BG_SECONDARY, 
            corner_radius=12,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR
        )
        self.profile_card.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.profile_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.profile_card, 
            text="💼 BUSINESS PROFILE", 
            font=Theme.FONT_SUBTITLE,
            text_color=Theme.TEXT_PRIMARY
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(15, 10))

        # Fields
        ctk.CTkLabel(self.profile_card, text="Business Name", font=Theme.FONT_BODY_BOLD).grid(row=1, column=0, sticky="w", padx=20, pady=6)
        self.biz_name_entry = ctk.CTkEntry(self.profile_card, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS)
        self.biz_name_entry.grid(row=1, column=1, sticky="ew", padx=(10, 20), pady=6)

        ctk.CTkLabel(self.profile_card, text="Owner Name", font=Theme.FONT_BODY_BOLD).grid(row=2, column=0, sticky="w", padx=20, pady=6)
        self.biz_owner_entry = ctk.CTkEntry(self.profile_card, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS)
        self.biz_owner_entry.grid(row=2, column=1, sticky="ew", padx=(10, 20), pady=6)

        ctk.CTkLabel(self.profile_card, text="Phone Number", font=Theme.FONT_BODY_BOLD).grid(row=3, column=0, sticky="w", padx=20, pady=6)
        self.biz_phone_entry = ctk.CTkEntry(self.profile_card, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS)
        self.biz_phone_entry.grid(row=3, column=1, sticky="ew", padx=(10, 20), pady=6)

        ctk.CTkLabel(self.profile_card, text="Address", font=Theme.FONT_BODY_BOLD).grid(row=4, column=0, sticky="w", padx=20, pady=6)
        self.biz_addr_entry = ctk.CTkEntry(self.profile_card, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS)
        self.biz_addr_entry.grid(row=4, column=1, sticky="ew", padx=(10, 20), pady=6)

        self.save_profile_btn = ctk.CTkButton(
            self.profile_card, text="Save Changes", font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER, command=self.save_profile
        )
        self.save_profile_btn.grid(row=5, column=1, sticky="e", padx=(0, 20), pady=(10, 15))

    def create_notifications_card(self):
        """🔔 Notification Preferences Card"""
        self.notifications_card = ctk.CTkFrame(
            self.cards_frame, 
            fg_color=Theme.BG_SECONDARY, 
            corner_radius=12,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR
        )
        self.notifications_card.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.notifications_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.notifications_card, 
            text="🔔 NOTIFICATION PREFERENCES", 
            font=Theme.FONT_SUBTITLE,
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w", padx=20, pady=(15, 10))

        # Checkboxes/Switches for preferences
        self.startup_notify_var = ctk.BooleanVar(value=True)
        self.startup_notify_sw = ctk.CTkSwitch(
            self.notifications_card, text="Startup Notification", 
            variable=self.startup_notify_var, font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.BORDER_COLOR, progress_color=Theme.ACCENT, command=self.save_notifications
        )
        self.startup_notify_sw.pack(anchor="w", padx=30, pady=8)

        self.shutdown_notify_var = ctk.BooleanVar(value=True)
        self.shutdown_notify_sw = ctk.CTkSwitch(
            self.notifications_card, text="Shutdown Notification", 
            variable=self.shutdown_notify_var, font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.BORDER_COLOR, progress_color=Theme.ACCENT, command=self.save_notifications
        )
        self.shutdown_notify_sw.pack(anchor="w", padx=30, pady=8)

        self.daily_report_var = ctk.BooleanVar(value=True)
        self.daily_report_sw = ctk.CTkSwitch(
            self.notifications_card, text="Generate Daily Report PDF", 
            variable=self.daily_report_var, font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.BORDER_COLOR, progress_color=Theme.ACCENT, command=self.save_notifications
        )
        self.daily_report_sw.pack(anchor="w", padx=30, pady=8)

        self.wa_delivery_var = ctk.BooleanVar(value=False)
        self.wa_delivery_sw = ctk.CTkSwitch(
            self.notifications_card, text="WhatsApp Report Delivery", 
            variable=self.wa_delivery_var, font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.BORDER_COLOR, progress_color=Theme.ACCENT, command=self.save_notifications
        )
        self.wa_delivery_sw.pack(anchor="w", padx=30, pady=(8, 20))

    def create_backup_card(self):
        """💾 Backup & Restore Maintenance Card"""
        self.backup_card = ctk.CTkFrame(
            self.cards_frame, 
            fg_color=Theme.BG_SECONDARY, 
            corner_radius=12,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR
        )
        self.backup_card.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        self.backup_card.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            self.backup_card, 
            text="💾 BACKUP & DATABASE", 
            font=Theme.FONT_SUBTITLE,
            text_color=Theme.TEXT_PRIMARY
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(15, 5))

        self.last_backup_lbl = ctk.CTkLabel(
            self.backup_card, 
            text="Last Backup: Never", 
            font=Theme.FONT_BODY,
            text_color=Theme.TEXT_SECONDARY
        )
        self.last_backup_lbl.grid(row=1, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 10))

        # Actions
        self.backup_btn = ctk.CTkButton(
            self.backup_card, text="Backup Now", font=Theme.FONT_BODY_BOLD,
            fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY, command=self.backup_database
        )
        self.backup_btn.grid(row=2, column=0, padx=(20, 5), pady=8, sticky="ew")

        self.restore_btn = ctk.CTkButton(
            self.backup_card, text="Restore Backup", font=Theme.FONT_BODY_BOLD,
            fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY, command=self.restore_database
        )
        self.restore_btn.grid(row=2, column=1, padx=(5, 20), pady=8, sticky="ew")

        self.folder_btn = ctk.CTkButton(
            self.backup_card, text="Open Backup Folder", font=Theme.FONT_BODY_BOLD,
            fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY, command=self.open_backup_folder
        )
        self.folder_btn.grid(row=3, column=0, columnspan=2, padx=20, pady=(5, 10), sticky="ew")

        self.purge_btn = ctk.CTkButton(
            self.backup_card, text="🚨 Clear All Data", font=Theme.FONT_BODY_BOLD,
            fg_color="transparent", hover_color=Theme.DANGER_HOVER,
            border_width=Theme.BORDER_WIDTH, border_color=Theme.DEBIT_RED,
            text_color=Theme.DEBIT_RED, command=self.purge_database
        )
        self.purge_btn.grid(row=4, column=0, columnspan=2, padx=20, pady=(5, 15), sticky="ew")

    def create_report_settings_card(self):
        """📈 Report Configuration Card"""
        self.report_settings_card = ctk.CTkFrame(
            self.cards_frame, 
            fg_color=Theme.BG_SECONDARY, 
            corner_radius=12,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR
        )
        self.report_settings_card.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        self.report_settings_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.report_settings_card, 
            text="📈 REPORT CONFIGURATION", 
            font=Theme.FONT_SUBTITLE,
            text_color=Theme.TEXT_PRIMARY
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(15, 10))

        # Folder Browse Option
        ctk.CTkLabel(self.report_settings_card, text="Export Folder", font=Theme.FONT_BODY_BOLD).grid(row=1, column=0, sticky="w", padx=20, pady=6)
        
        self.folder_entry_frame = ctk.CTkFrame(self.report_settings_card, fg_color="transparent")
        self.folder_entry_frame.grid(row=1, column=1, sticky="ew", padx=(10, 20), pady=6)
        self.folder_entry_frame.grid_columnconfigure(0, weight=1)
        
        self.export_folder_entry = ctk.CTkEntry(self.folder_entry_frame, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS)
        self.export_folder_entry.grid(row=0, column=0, sticky="ew")
        
        self.browse_btn = ctk.CTkButton(
            self.folder_entry_frame, text="Browse", font=Theme.FONT_CAPTION,
            width=60, fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY, command=self.browse_export_folder
        )
        self.browse_btn.grid(row=0, column=1, padx=(5, 0))

        ctk.CTkLabel(self.report_settings_card, text="PDF Name Format", font=Theme.FONT_BODY_BOLD).grid(row=2, column=0, sticky="w", padx=20, pady=6)
        self.pdf_format_entry = ctk.CTkEntry(self.report_settings_card, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS)
        self.pdf_format_entry.grid(row=2, column=1, sticky="ew", padx=(10, 20), pady=6)

        self.auto_reports_var = ctk.BooleanVar(value=True)
        self.auto_reports_sw = ctk.CTkSwitch(
            self.report_settings_card, text="Auto Generate Daily Reports", 
            variable=self.auto_reports_var, font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.BORDER_COLOR, progress_color=Theme.ACCENT, command=self.save_report_settings
        )
        self.auto_reports_sw.grid(row=3, column=1, sticky="w", padx=(10, 20), pady=(8, 15))

    def create_about_card(self):
        """ℹ️ System Information (About) Card"""
        self.about_card = ctk.CTkFrame(
            self.cards_frame, 
            fg_color=Theme.BG_SECONDARY, 
            corner_radius=12,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR
        )
        self.about_card.grid(row=2, column=1, padx=10, pady=10, sticky="nsew")
        self.about_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.about_card, 
            text="ℹ️ SYSTEM INFORMATION", 
            font=Theme.FONT_SUBTITLE,
            text_color=Theme.TEXT_PRIMARY
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(15, 10))

        # Metrics lists
        metrics = [
            ("Application Version", "version_lbl", "v1.1.0"),
            ("Database File Size", "db_size_lbl", "0 KB"),
            ("Active Customers", "active_cust_lbl", "0"),
            ("Logged Transactions", "logged_txns_lbl", "0")
        ]
        
        self.metric_labels = {}
        for idx, (label_text, var_name, default_val) in enumerate(metrics, start=1):
            ctk.CTkLabel(self.about_card, text=label_text, font=Theme.FONT_BODY_BOLD, text_color=Theme.TEXT_SECONDARY).grid(row=idx, column=0, sticky="w", padx=20, pady=5)
            
            lbl = ctk.CTkLabel(self.about_card, text=default_val, font=Theme.FONT_BODY_BOLD, text_color=Theme.TEXT_PRIMARY)
            lbl.grid(row=idx, column=1, sticky="e", padx=20, pady=5)
            self.metric_labels[var_name] = lbl

    def create_pdf_security_card(self):
        """🔒 PDF Security Card — password protection for all exported PDFs."""
        self.pdf_security_card = ctk.CTkFrame(
            self.cards_frame,
            fg_color=Theme.BG_SECONDARY,
            corner_radius=12,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR
        )
        # Full-width: spans both columns below the 3 existing rows
        self.pdf_security_card.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.pdf_security_card.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # ── Card Header row ──────────────────────────────────────────────
        header_row = ctk.CTkFrame(self.pdf_security_card, fg_color="transparent")
        header_row.grid(row=0, column=0, columnspan=4, sticky="ew", padx=20, pady=(15, 0))
        header_row.grid_columnconfigure(1, weight=1)

        # Shield icon + title
        ctk.CTkLabel(
            header_row,
            text="🔒",
            font=(Theme.FONT_FAMILY, 22),
        ).grid(row=0, column=0, padx=(0, 8))

        ctk.CTkLabel(
            header_row,
            text="PDF SECURITY",
            font=Theme.FONT_SUBTITLE,
            text_color=Theme.TEXT_PRIMARY,
            anchor="w"
        ).grid(row=0, column=1, sticky="w")

        # Status indicator pill (right side)
        self.pdf_sec_status_pill = ctk.CTkLabel(
            header_row,
            text="● DISABLED",
            font=Theme.FONT_BODY_BOLD,
            text_color=Theme.TEXT_SECONDARY
        )
        self.pdf_sec_status_pill.grid(row=0, column=2, sticky="e")

        # ── Separator ────────────────────────────────────────────────────
        sep = ctk.CTkFrame(self.pdf_security_card, fg_color=Theme.BORDER_COLOR, height=1)
        sep.grid(row=1, column=0, columnspan=4, sticky="ew", padx=20, pady=(10, 0))

        # ── Left column: Enable toggle + password fields ─────────────────
        left_col = ctk.CTkFrame(self.pdf_security_card, fg_color="transparent")
        left_col.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=(20, 10), pady=15)
        left_col.grid_columnconfigure(0, weight=1)

        # Enable toggle
        self.pdf_sec_enabled_var = ctk.BooleanVar(value=False)
        self.pdf_sec_sw = ctk.CTkSwitch(
            left_col,
            text="Enable PDF Password Protection",
            variable=self.pdf_sec_enabled_var,
            font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.BORDER_COLOR,
            progress_color=Theme.ACCENT,
            command=self._on_pdf_security_toggle
        )
        self.pdf_sec_sw.grid(row=0, column=0, sticky="w", pady=(0, 12))

        # Password field row
        pw_row = ctk.CTkFrame(left_col, fg_color="transparent")
        pw_row.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        pw_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(pw_row, text="Password", font=Theme.FONT_BODY_BOLD, width=100, anchor="w").grid(row=0, column=0, sticky="w")
        self.pdf_pw_entry = ctk.CTkEntry(
            pw_row,
            font=Theme.FONT_BODY,
            corner_radius=Theme.CORNER_RADIUS,
            show="●",
            placeholder_text="e.g. Ledger@2026"
        )
        self.pdf_pw_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.pdf_pw_entry.bind("<KeyRelease>", self._update_strength_meter)

        # Confirm field row
        cf_row = ctk.CTkFrame(left_col, fg_color="transparent")
        cf_row.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        cf_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(cf_row, text="Confirm", font=Theme.FONT_BODY_BOLD, width=100, anchor="w").grid(row=0, column=0, sticky="w")
        self.pdf_cf_entry = ctk.CTkEntry(
            cf_row,
            font=Theme.FONT_BODY,
            corner_radius=Theme.CORNER_RADIUS,
            show="●",
            placeholder_text="Re-enter password"
        )
        self.pdf_cf_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        # Show/Hide toggle
        self._pdf_pw_visible = False
        self.show_pw_btn = ctk.CTkButton(
            left_col,
            text="👁  Show Password",
            font=Theme.FONT_CAPTION,
            fg_color="transparent",
            hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_SECONDARY,
            width=140,
            command=self._toggle_pdf_password_visibility
        )
        self.show_pw_btn.grid(row=3, column=0, sticky="w", pady=(0, 12))

        # Action buttons row
        btn_row = ctk.CTkFrame(left_col, fg_color="transparent")
        btn_row.grid(row=4, column=0, sticky="ew")

        self.save_pw_btn = ctk.CTkButton(
            btn_row,
            text="💾  Save Password",
            font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.ACCENT,
            hover_color=Theme.ACCENT_HOVER,
            command=self._save_pdf_password
        )
        self.save_pw_btn.pack(side="left", padx=(0, 8))

        self.change_pw_btn = ctk.CTkButton(
            btn_row,
            text="🔄  Change Password",
            font=Theme.FONT_BODY_BOLD,
            fg_color="transparent",
            hover_color=Theme.BG_TERTIARY,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY,
            command=self._open_change_password_dialog
        )
        self.change_pw_btn.pack(side="left")

        # Feedback label (success / error messages)
        self.pdf_sec_msg_lbl = ctk.CTkLabel(
            left_col,
            text="",
            font=Theme.FONT_CAPTION,
            text_color=Theme.TEXT_SECONDARY,
            anchor="w",
            wraplength=380
        )
        self.pdf_sec_msg_lbl.grid(row=5, column=0, sticky="w", pady=(8, 0))

        # ── Right column: Strength meter + info panel ────────────────────
        right_col = ctk.CTkFrame(self.pdf_security_card, fg_color="transparent")
        right_col.grid(row=2, column=2, columnspan=2, sticky="nsew", padx=(10, 20), pady=15)
        right_col.grid_columnconfigure(0, weight=1)

        # Strength meter label
        ctk.CTkLabel(
            right_col,
            text="Password Strength",
            font=Theme.FONT_BODY_BOLD,
            text_color=Theme.TEXT_SECONDARY,
            anchor="w"
        ).grid(row=0, column=0, sticky="w")

        # Strength meter bar (4 segments)
        meter_frame = ctk.CTkFrame(right_col, fg_color="transparent")
        meter_frame.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        for i in range(4):
            meter_frame.grid_columnconfigure(i, weight=1)

        self._strength_bars = []
        for i in range(4):
            bar = ctk.CTkProgressBar(
                meter_frame,
                height=8,
                corner_radius=4,
                mode="determinate",
                progress_color=Theme.BORDER_COLOR,
                fg_color=Theme.BG_TERTIARY
            )
            bar.set(1.0)
            bar.grid(row=0, column=i, sticky="ew", padx=2)
            self._strength_bars.append(bar)

        self.strength_lbl = ctk.CTkLabel(
            right_col,
            text="Enter a password above",
            font=Theme.FONT_CAPTION,
            text_color=Theme.TEXT_SECONDARY,
            anchor="w"
        )
        self.strength_lbl.grid(row=2, column=0, sticky="w", pady=(4, 12))

        # Policy info box
        policy_box = ctk.CTkFrame(
            right_col,
            fg_color=Theme.BG_TERTIARY,
            corner_radius=8,
            border_width=1,
            border_color=Theme.BORDER_COLOR
        )
        policy_box.grid(row=3, column=0, sticky="nsew", pady=(0, 4))
        policy_box.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            policy_box,
            text="Password Policy",
            font=Theme.FONT_BODY_BOLD,
            text_color=Theme.TEXT_PRIMARY,
            anchor="w"
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        policy_lines = [
            "✔  Minimum 8 characters",
            "✔  At least one uppercase letter (A-Z)",
            "✔  At least one lowercase letter (a-z)",
            "✔  At least one number (0-9)",
            "✔  At least one special character (@, #, !...)",
            "  e.g.  Ledger@2026",
        ]
        for i, line in enumerate(policy_lines, start=1):
            ctk.CTkLabel(
                policy_box,
                text=line,
                font=Theme.FONT_CAPTION,
                text_color=Theme.TEXT_SECONDARY,
                anchor="w"
            ).grid(row=i, column=0, sticky="w", padx=12, pady=1)

        ctk.CTkLabel(policy_box, text="").grid(row=len(policy_lines)+1, column=0, pady=4)

        # Initial load of state
        self._load_pdf_security_state()

    def refresh(self):
        """Called by app shell when Settings view transitions into focus."""
        self.load_settings(load_profile_entries=False)
        self.update_about_stats()

    def update_about_stats(self):
        """Queries database stats dynamically to populate the System Info card."""
        cust_count = 0
        txn_count = 0
        db_size_str = "0 KB"
        
        try:
            with self.db_manager.get_connection() as conn:
                cust_count = conn.execute("SELECT COUNT(*) FROM customers;").fetchone()[0]
                txn_count = conn.execute("SELECT COUNT(*) FROM transactions;").fetchone()[0]
        except Exception as e:
            print(f"Error querying statistics: {e}")
            
        try:
            db_path = self.db_manager.db_path
            if os.path.exists(db_path):
                sz = os.path.getsize(db_path)
                if sz < 1024 * 1024:
                    db_size_str = f"{sz / 1024:.1f} KB"
                else:
                    db_size_str = f"{sz / (1024 * 1024):.1f} MB"
        except Exception as e:
            print(f"Error querying database size: {e}")

        # Update labels
        self.metric_labels["active_cust_lbl"].configure(text=str(cust_count))
        self.metric_labels["logged_txns_lbl"].configure(text=str(txn_count))
        self.metric_labels["db_size_lbl"].configure(text=db_size_str)

    def load_settings(self, load_profile_entries=False):
        """Loads business configurations from settings.json."""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    
                    # 1. Themes Preview
                    current_theme = data.get("theme", "dark")
                    self.draw_theme_previews(current_theme)

                    # 2. Profile Cards
                    if load_profile_entries:
                        self.biz_name_entry.delete(0, "end")
                        self.biz_name_entry.insert(0, data.get("name", ""))
                        
                        self.biz_owner_entry.delete(0, "end")
                        self.biz_owner_entry.insert(0, data.get("owner_name", ""))
                        
                        self.biz_phone_entry.delete(0, "end")
                        self.biz_phone_entry.insert(0, data.get("business_phone", ""))
                        
                        self.biz_addr_entry.delete(0, "end")
                        self.biz_addr_entry.insert(0, data.get("address", ""))

                    # 3. Notification Settings
                    self.startup_notify_var.set(data.get("startup_notification", True))
                    self.shutdown_notify_var.set(data.get("shutdown_notification", True))
                    self.daily_report_var.set(data.get("generate_daily_report", True))
                    self.wa_delivery_var.set(data.get("whatsapp_delivery", False))

                    # 4. Report Settings
                    if load_profile_entries:
                        self.export_folder_entry.delete(0, "end")
                        self.export_folder_entry.insert(0, data.get("default_export_folder", "reports"))
                        
                        self.pdf_format_entry.delete(0, "end")
                        self.pdf_format_entry.insert(0, data.get("default_pdf_format", "Daily_Summary_{date}"))
                    
                    self.auto_reports_var.set(data.get("auto_generate_daily_reports", True))

                    # 5. Maintenance Settings
                    last_backup = data.get("last_backup_date", "Never")
                    self.last_backup_lbl.configure(text=f"Last Backup: {last_backup}")

            except Exception as e:
                print(f"Error loading settings: {e}")
        else:
            # Fallback draw
            self.draw_theme_previews("dark")

    def change_theme(self, theme_name: str):
        """Switches theme instantly."""
        ThemeManager.set_theme(theme_name)
        # Redraw previews to toggle checkmarks
        self.draw_theme_previews(theme_name)

    def save_profile(self):
        """Saves business profile details in settings.json configuration file."""
        data = {}
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
            except Exception:
                pass

        data.update({
            "name": self.biz_name_entry.get().strip(),
            "owner_name": self.biz_owner_entry.get().strip(),
            "business_phone": self.biz_phone_entry.get().strip(),
            "address": self.biz_addr_entry.get().strip()
        })
        
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=4)
            messagebox.showinfo("Profile Saved", "Business profile saved successfully!")
        except Exception as e:
            messagebox.showerror("Error Saving Settings", f"Could not write configuration: {e}")

    def save_notifications(self):
        """Saves notification preference toggles directly on interact click events."""
        data = {}
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
            except Exception:
                pass

        data.update({
            "startup_notification": self.startup_notify_var.get(),
            "shutdown_notification": self.shutdown_notify_var.get(),
            "generate_daily_report": self.daily_report_var.get(),
            "whatsapp_delivery": self.wa_delivery_var.get()
        })
        
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving notification configurations: {e}")

    def save_report_settings(self):
        """Saves reports preferences directly on toggles or entry saves."""
        data = {}
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
            except Exception:
                pass

        data.update({
            "default_export_folder": self.export_folder_entry.get().strip(),
            "default_pdf_format": self.pdf_format_entry.get().strip(),
            "auto_generate_daily_reports": self.auto_reports_var.get()
        })

        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving report settings: {e}")

    def browse_export_folder(self):
        """Launches directory picker dialog and binds output to export path field."""
        folder = filedialog.askdirectory(title="Select Default Exports Folder")
        if folder:
            self.export_folder_entry.delete(0, "end")
            self.export_folder_entry.insert(0, folder)
            self.save_report_settings()

    def backup_database(self):
        """Copies active sqlite database to a user-selected path."""
        file_path = filedialog.asksaveasfilename(
            title="Choose Backup File Path",
            defaultextension=".db",
            filetypes=[("SQLite Databases", "*.db")],
            initialfile=f"Ledger_Backup_{datetime.date.today().strftime('%Y%m%d')}.db"
        )
        
        if file_path:
            try:
                src_path = self.db_manager.db_path
                shutil.copy2(src_path, file_path)
                
                # Update last backup date in configurations
                backup_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                data = {}
                if os.path.exists(SETTINGS_FILE):
                    try:
                        with open(SETTINGS_FILE, "r") as f:
                            data = json.load(f)
                    except Exception:
                        pass
                
                data["last_backup_date"] = backup_time
                with open(SETTINGS_FILE, "w") as f:
                    json.dump(data, f, indent=4)

                self.last_backup_lbl.configure(text=f"Last Backup: {backup_time}")
                messagebox.showinfo("Backup Completed", f"Database backed up successfully at:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Backup Failed", f"An error occurred copying files: {e}")

    def restore_database(self):
        """Restores a database file from backup, replacing the current active db."""
        file_path = filedialog.askopenfilename(
            title="Select Backup File to Restore",
            filetypes=[("SQLite Databases", "*.db")]
        )
        
        if file_path:
            confirm = messagebox.askyesno(
                "Confirm Restore", 
                "Are you sure you want to restore this database?\nThis will completely replace all current ledger records!", 
                icon="warning"
            )
            if confirm:
                try:
                    dest_path = self.db_manager.db_path
                    shutil.copy2(file_path, dest_path)
                    
                    self.db_manager.init_db()
                    messagebox.showinfo("Restore Successful", "Database restored successfully!")
                    
                    # Refresh statistics and triggers resets
                    self.update_about_stats()
                    self.on_db_reset()
                except Exception as e:
                    messagebox.showerror("Restore Failed", f"An error occurred copying files: {e}")

    def open_backup_folder(self):
        """Opens the folder containing backups using the OS file manager."""
        backup_dir = os.path.abspath(os.path.dirname(self.db_manager.db_path))
        try:
            if os.name == 'nt':
                os.startfile(backup_dir)
            else:
                subprocess.Popen(['xdg-open', backup_dir])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")

    def purge_database(self):
        """Deletes all records from customers and transactions, resetting the ledger to empty."""
        confirm = messagebox.askyesno(
            "Confirm Clear All Data", 
            "Are you absolutely sure you want to delete all customer records and transactions?\nThis action cannot be undone!", 
            icon="warning"
        )
        if confirm:
            try:
                with self.db_manager.get_connection() as conn:
                    conn.execute("DELETE FROM transactions;")
                    conn.execute("DELETE FROM customers;")
                    conn.execute("DELETE FROM sqlite_sequence;")
                
                messagebox.showinfo("Clean Completed", "All database tables cleared successfully!")
                self.update_about_stats()
                self.on_db_reset()
            except Exception as e:
                messagebox.showerror("Operation Failed", f"Database purge failed: {e}")

    # ================================================================== #
    #  PDF Security Card — Event Handlers
    # ================================================================== #

    def _load_pdf_security_state(self):
        """Reads settings.json and reflects the current PDF security state in the UI."""
        try:
            sec = PdfSecurityService.load_pdf_security_settings()
            enabled  = sec.get("pdf_security_enabled", False)
            has_hash = bool(sec.get("password_hash", ""))

            self.pdf_sec_enabled_var.set(enabled)
            self._refresh_status_pill(enabled, has_hash)
        except Exception as e:
            print(f"[Settings] Error loading PDF security state: {e}")

    def _refresh_status_pill(self, enabled: bool, has_password: bool):
        """Updates the coloured status pill in the card header."""
        if enabled and has_password:
            self.pdf_sec_status_pill.configure(
                text="● PROTECTED",
                text_color="#22C55E"   # green
            )
        elif enabled and not has_password:
            self.pdf_sec_status_pill.configure(
                text="● NO PASSWORD SET",
                text_color="#F59E0B"   # amber warning
            )
        else:
            self.pdf_sec_status_pill.configure(
                text="● DISABLED",
                text_color=Theme.TEXT_SECONDARY
            )

    def _on_pdf_security_toggle(self):
        """Handles the Enable/Disable switch toggle — saves immediately."""
        enabled = self.pdf_sec_enabled_var.get()
        try:
            PdfSecurityService.set_enabled(enabled)
            sec = PdfSecurityService.load_pdf_security_settings()
            has_hash = bool(sec.get("password_hash", ""))
            self._refresh_status_pill(enabled, has_hash)

            if enabled and not has_hash:
                self._show_pdf_msg(
                    "⚠  Security enabled — please set a password below and click Save Password.",
                    color="#F59E0B"
                )
            elif enabled:
                self._show_pdf_msg("✔  PDF password protection is now active.", color="#22C55E")
            else:
                self._show_pdf_msg("PDF password protection disabled.", color=Theme.TEXT_SECONDARY)
        except Exception as e:
            self._show_pdf_msg(f"Error saving toggle: {e}", color="#EF4444")

    def _update_strength_meter(self, event=None):
        """Re-draws the 4-segment strength bar on every keystroke in the password field."""
        password = self.pdf_pw_entry.get()
        score = PdfSecurityService.get_password_strength_score(password)

        # Colour palette per score level
        colours = ["#EF4444", "#F97316", "#EAB308", "#22C55E"]  # red, orange, yellow, green
        labels  = ["Very Weak", "Weak", "Fair", "Strong", "Very Strong"]

        active_colour = colours[min(score, 3)] if score > 0 else Theme.BORDER_COLOR

        for i, bar in enumerate(self._strength_bars):
            if i < score:
                bar.configure(progress_color=active_colour)
            else:
                bar.configure(progress_color=Theme.BORDER_COLOR)

        if not password:
            self.strength_lbl.configure(
                text="Enter a password above",
                text_color=Theme.TEXT_SECONDARY
            )
        else:
            self.strength_lbl.configure(
                text=f"Strength: {labels[score]}",
                text_color=active_colour
            )

    def _toggle_pdf_password_visibility(self):
        """Toggles show/hide for both password entry fields."""
        self._pdf_pw_visible = not self._pdf_pw_visible
        char = "" if self._pdf_pw_visible else "●"
        self.pdf_pw_entry.configure(show=char)
        self.pdf_cf_entry.configure(show=char)
        label = "🙈  Hide Password" if self._pdf_pw_visible else "👁  Show Password"
        self.show_pw_btn.configure(text=label)

    def _show_pdf_msg(self, text: str, color: str = None, auto_clear: bool = True):
        """Displays a feedback message under the action buttons, auto-clears after 5 s."""
        self.pdf_sec_msg_lbl.configure(
            text=text,
            text_color=color or Theme.TEXT_SECONDARY
        )
        if auto_clear:
            self.after(5000, lambda: self.pdf_sec_msg_lbl.configure(text=""))

    def _save_pdf_password(self):
        """
        Validates, hashes, and saves a new PDF password from the Settings card.
        Requires both password and confirm fields to match and pass strength policy.
        """
        password = self.pdf_pw_entry.get()
        confirm  = self.pdf_cf_entry.get()

        # 1. Strength validation
        ok, reason = PdfSecurityService.validate_password_strength(password)
        if not ok:
            self._show_pdf_msg(f"❌  {reason}", color="#EF4444")
            return

        # 2. Confirm match
        if password != confirm:
            self._show_pdf_msg("❌  Passwords do not match. Please re-enter both fields.", color="#EF4444")
            return

        # 3. Hash and save
        try:
            salt_hex, hash_hex = PdfSecurityService.hash_password(password)
            enabled = self.pdf_sec_enabled_var.get()
            PdfSecurityService.save_pdf_security_settings(
                enabled=enabled,
                password_hash=hash_hex,
                salt=salt_hex,
                raw_password=password      # stored XOR-obfuscated, never plaintext
            )

            # Clear entry fields after save
            self.pdf_pw_entry.delete(0, "end")
            self.pdf_cf_entry.delete(0, "end")
            self._update_strength_meter()

            self._refresh_status_pill(enabled, True)
            self._show_pdf_msg(
                "✔  Password saved successfully. All future PDF exports will be encrypted.",
                color="#22C55E"
            )
        except Exception as e:
            self._show_pdf_msg(f"❌  Failed to save password: {e}", color="#EF4444")

    def _open_change_password_dialog(self):
        """Opens the Change Password modal dialog."""
        sec = PdfSecurityService.load_pdf_security_settings()
        if not sec.get("password_hash"):
            self._show_pdf_msg(
                "⚠  No password is set yet. Use 'Save Password' to set one first.",
                color="#F59E0B"
            )
            return
        PasswordChangeDialog(self, on_success=self._on_password_changed)

    def _on_password_changed(self):
        """Callback invoked by PasswordChangeDialog after a successful password change."""
        self._load_pdf_security_state()
        self._show_pdf_msg(
            "✔  Password changed successfully. New password will apply to all future exports.",
            color="#22C55E"
        )


# ====================================================================== #
#  Password Change Dialog
# ====================================================================== #

