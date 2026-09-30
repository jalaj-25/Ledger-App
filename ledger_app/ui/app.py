import customtkinter as ctk
import os
import json
import datetime
from ledger_app.ui.theme import Theme
from ledger_app.database.db_connection import DatabaseManager
from ledger_app.repositories.customer_repository import CustomerRepository
from ledger_app.repositories.transaction_repository import TransactionRepository
from ledger_app.repositories.payment_mode_repository import PaymentModeRepository
from ledger_app.repositories.user_repository import UserRepository
from ledger_app.repositories.audit_repository import AuditRepository

from ledger_app.services.customer_service import CustomerService
from ledger_app.services.transaction_service import TransactionService
from ledger_app.services.ledger_service import LedgerService
from ledger_app.services.report_service import ReportService
from ledger_app.services.export_service import ExportService
from ledger_app.services.notification_service import NotificationService
from ledger_app.services.whatsapp_service import WhatsAppService
from ledger_app.services.email_service import EmailService
from ledger_app.services.analytics_service import AnalyticsService
from ledger_app.services.auth_service import AuthService
from ledger_app.services.user_management_service import UserManagementService
from ledger_app.services.audit_service import AuditService, AuditAction
from ledger_app.services.session_manager import SessionManager
from ledger_app.models.user import Permission
from ledger_app.backup_manager import BackupManager

# Import Screens
from ledger_app.ui.screens.dashboard import DashboardScreen
from ledger_app.ui.screens.customer_management import CustomerManagementScreen
from ledger_app.ui.screens.transaction_entry import TransactionEntryScreen
from ledger_app.ui.screens.reports import ReportsScreen
from ledger_app.ui.screens.ledger_view import LedgerViewScreen
from ledger_app.ui.screens.settings import SettingsScreen
from ledger_app.ui.screens.import_wizard import ImportScreen
from ledger_app.ui.screens.login_screen import LoginScreen
from ledger_app.ui.screens.user_management import UserManagementScreen

SETTINGS_FILE = "settings.json"
INACTIVITY_CHECK_MS = 60_000   # Check every 60 seconds


class App(ctk.CTk):
    """
    Main shell container. Handles:
      - Dependency injection (DB, repos, services)
      - Authentication and session lifecycle
      - Role-based sidebar navigation
      - Inactivity timer
      - Audit logging wrappers around key actions
    """

    def __init__(self):
        super().__init__()

        # Preprocess settings to hash/obfuscate any plaintext credentials
        try:
            from ledger_app.services.settings_preprocessor import preprocess_settings
            preprocess_settings()
        except Exception as e:
            print(f"[App] Error executing settings preprocessor: {e}")

        self.title("Ledger Management System")
        self.geometry("1100x680")
        self.minimum_width = 1000
        self.minimum_height = 600
        self.minsize(self.minimum_width, self.minimum_height)

        from ledger_app.ui.theme_manager import ThemeManager
        ThemeManager.load_theme()
        ThemeManager.apply_theme()
        self.configure(fg_color=Theme.BG_PRIMARY)

        # ── Dependency Injection ──────────────────────────────────────────────
        self.db = DatabaseManager(db_path="ledger.db")

        # Core repos
        self.customer_repo      = CustomerRepository(self.db)
        self.transaction_repo   = TransactionRepository(self.db)
        self.payment_mode_repo  = PaymentModeRepository(self.db)
        self.user_repo          = UserRepository(self.db)
        self.audit_repo         = AuditRepository(self.db)

        # Core services
        self.customer_service    = CustomerService(self.customer_repo)
        self.transaction_service = TransactionService(self.transaction_repo, self.customer_repo, self.payment_mode_repo)
        self.ledger_service      = LedgerService(self.customer_repo, self.transaction_repo)
        self.report_service      = ReportService(self.db)
        self.analytics_service   = AnalyticsService(self.db)
        self.export_service      = ExportService()
        self.notification_service = NotificationService()
        self.whatsapp_service    = WhatsAppService(self)
        self.email_service       = EmailService()

        # Auth + user management services
        self.auth_service        = AuthService(self.user_repo)
        self.audit_service       = AuditService(self.audit_repo)
        self.user_mgmt_service   = UserManagementService(self.user_repo, self.auth_service)

        # Backup Manager
        self.backup_manager = BackupManager()
        self.backup_manager.initialize(
            db_path              = self.db.db_path,
            settings_file        = SETTINGS_FILE,
            notification_service = self.notification_service,
        )

        # ── Layout ────────────────────────────────────────────────────────────
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Sidebar ───────────────────────────────────────────────────────────
        self.sidebar_frame = ctk.CTkFrame(
            self, fg_color=Theme.BG_SIDEBAR, width=200, corner_radius=0
        )
        self.sidebar_frame.grid_columnconfigure(0, weight=1)
        # Rows: 0=logo, 1-5=nav, 6=spacer, 7=user_widget, 8=logout
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        self.logo_lbl = ctk.CTkLabel(
            self.sidebar_frame,
            text="JALAJ LEDGER",
            font=Theme.FONT_SUBTITLE,
            text_color=Theme.ACCENT
        )
        self.logo_lbl.grid(row=0, column=0, padx=20, pady=25)

        # Nav items: (label, row, icon, required_permission or None)
        self._nav_items = [
            ("Dashboard", 1, "📊", None),
            ("Customers", 2, "👤", None),
            ("New Entry", 3, "✍️", Permission.ADD_TRANSACTION),
            ("Reports",   4, "📈", Permission.VIEW_REPORTS),
            ("Import",    5, "📥", Permission.IMPORT_DATA),
        ]
        self.nav_buttons = {}
        for text, row, icon, perm in self._nav_items:
            btn = ctk.CTkButton(
                self.sidebar_frame,
                text=f"{icon}  {text}",
                font=Theme.FONT_BODY_BOLD,
                anchor="w",
                fg_color="transparent",
                hover_color=Theme.BG_TERTIARY,
                text_color=Theme.TEXT_PRIMARY,
                height=40,
                corner_radius=5,
                command=lambda name=text: self.switch_screen(name)
            )
            btn.grid(row=row, column=0, padx=15, pady=4, sticky="ew")
            self.nav_buttons[text] = btn

        # Users button (Owner only)
        self.users_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="👥  Users",
            font=Theme.FONT_BODY_BOLD,
            anchor="w",
            fg_color="transparent",
            hover_color=Theme.BG_TERTIARY,
            text_color=Theme.TEXT_PRIMARY,
            height=40,
            corner_radius=5,
            command=lambda: self.switch_screen("Users")
        )
        self.users_btn.grid(row=6, column=0, padx=15, pady=4, sticky="sew")
        self.nav_buttons["Users"] = self.users_btn

        # Settings button
        self.settings_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="⚙️  Settings",
            font=Theme.FONT_BODY_BOLD,
            anchor="w",
            fg_color="transparent",
            hover_color=Theme.BG_TERTIARY,
            text_color=Theme.TEXT_PRIMARY,
            height=40,
            corner_radius=5,
            command=lambda: self.switch_screen("Settings")
        )
        self.settings_btn.grid(row=7, column=0, padx=15, pady=4, sticky="ew")
        self.nav_buttons["Settings"] = self.settings_btn

        # User info widget (bottom of sidebar)
        self.user_info_frame = ctk.CTkFrame(self.sidebar_frame, fg_color=Theme.BG_TERTIARY, corner_radius=8)
        self.user_info_frame.grid(row=8, column=0, padx=15, pady=(4, 4), sticky="ew")
        self.user_info_frame.grid_columnconfigure(0, weight=1)

        self.user_name_lbl = ctk.CTkLabel(
            self.user_info_frame, text="",
            font=Theme.FONT_BODY_BOLD, text_color=Theme.TEXT_PRIMARY, anchor="w"
        )
        self.user_name_lbl.grid(row=0, column=0, padx=10, pady=(8, 0), sticky="ew")

        self.user_role_lbl = ctk.CTkLabel(
            self.user_info_frame, text="",
            font=Theme.FONT_CAPTION, text_color=Theme.TEXT_SECONDARY, anchor="w"
        )
        self.user_role_lbl.grid(row=1, column=0, padx=10, pady=(0, 2), sticky="ew")

        self.user_login_lbl = ctk.CTkLabel(
            self.user_info_frame, text="",
            font=(Theme.FONT_FAMILY, 8), text_color=Theme.TEXT_SECONDARY, anchor="w"
        )
        self.user_login_lbl.grid(row=2, column=0, padx=10, pady=(0, 8), sticky="ew")

        # Logout button
        self.logout_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="🚪  Logout",
            font=Theme.FONT_BODY_BOLD,
            anchor="w",
            fg_color="transparent",
            hover_color=Theme.DANGER_HOVER,
            text_color=Theme.DEBIT_RED,
            border_width=1,
            border_color=Theme.DEBIT_RED,
            height=36,
            corner_radius=5,
            command=self.logout
        )
        self.logout_btn.grid(row=9, column=0, padx=15, pady=(2, 18), sticky="ew")

        # ── Screen Container ──────────────────────────────────────────────────
        self.container_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.container_frame.grid_columnconfigure(0, weight=1)
        self.container_frame.grid_rowconfigure(0, weight=1)

        # ── Instantiate Screens ───────────────────────────────────────────────
        self.screens = {
            "Dashboard": DashboardScreen(
                self.container_frame,
                self.customer_service,
                self.report_service,
                self.analytics_service
            ),
            "Customers": CustomerManagementScreen(
                self.container_frame,
                self.customer_service,
                on_view_ledger=lambda cid: self.switch_screen("Ledger", customer_id=cid),
                transaction_service=self.transaction_service,
                payment_mode_repo=self.payment_mode_repo,
                backup_manager=self.backup_manager
            ),
            "New Entry": TransactionEntryScreen(
                self.container_frame,
                self.customer_service,
                self.transaction_service,
                self.payment_mode_repo
            ),
            "Reports": ReportsScreen(
                self.container_frame,
                self.customer_service,
                self.report_service,
                self.export_service
            ),
            "Settings": SettingsScreen(
                self.container_frame,
                self.db,
                self.customer_service,
                self.transaction_service,
                self.report_service,
                on_db_reset=self.on_database_reset,
                backup_manager=self.backup_manager,
            ),
            "Import": ImportScreen(
                self.container_frame,
                self.customer_service,
                self.transaction_service,
                self.payment_mode_repo,
                backup_manager=self.backup_manager,
                on_import_complete=self.on_import_complete,
            ),
            "Ledger": LedgerViewScreen(
                self.container_frame,
                self.customer_service,
                self.ledger_service,
                self.transaction_service,
                self.payment_mode_repo,
                self.export_service,
                on_back=lambda: self.switch_screen("Customers"),
                analytics_service=self.analytics_service
            ),
            "Users": UserManagementScreen(
                self.container_frame,
                self.user_mgmt_service,
                self.audit_service
            ),
        }

        self.active_screen_name = "Dashboard"
        self._is_closing = False
        self.login_frame = None

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        from ledger_app.ui.theme_manager import ThemeManager
        ThemeManager.register_listener(self.on_theme_changed)

        # Show login
        if os.environ.get("TEST_MODE") == "1":
            self.start_main_app(None)
        else:
            self.show_login_screen()

    # ═══════════════════════════════════════════════════════════════════════
    #  AUTH FLOW
    # ═══════════════════════════════════════════════════════════════════════

    def show_login_screen(self, locked_user=None):
        """Shows the full-screen login frame."""
        self.login_frame = LoginScreen(
            self,
            on_success=self.start_main_app,
            auth_service=self.auth_service,
            audit_service=self.audit_service
        )
        if locked_user:
            self.login_frame.rebuild_as_lock_screen(locked_user)
        self.login_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")

    def start_main_app(self, user):
        """Called by LoginScreen on successful authentication."""
        # Destroy login frame
        if self.login_frame:
            try:
                self.login_frame.grid_forget()
                self.login_frame.destroy()
            except Exception:
                pass
            self.login_frame = None

        # Start session
        if user:
            SessionManager.start_session(user)
        else:
            # TEST_MODE: create a virtual owner session
            from ledger_app.models.user import User, ROLE_OWNER
            user = User(id=0, username="test_owner", role=ROLE_OWNER, is_active=True)
            SessionManager.start_session(user)

        # Check if must change password (except in TEST_MODE virtual owner)
        # Disabled forced password change per user requirements (passwords set by admin remain permanent)
        if False and user and user.id != 0 and user.must_change:
            def handle_password_changed(force_logout=False):
                if force_logout:
                    self.logout()
                else:
                    self._initialize_main_ui(user)

            # Hide main app shell elements first (so user is blocked in dialog)
            self.sidebar_frame.grid_forget()
            self.container_frame.grid_forget()
            
            StaffForcePasswordChangeDialog(
                self, user, self.auth_service, self.audit_service, handle_password_changed
            )
        else:
            self._initialize_main_ui(user)

    def _initialize_main_ui(self, user):
        # Update sidebar
        self._update_user_widget(user)
        self._apply_role_nav_visibility(user)

        # Grid sidebar + container
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.container_frame.grid(row=0, column=1, padx=30, pady=30, sticky="nsew")

        # Show dashboard
        self.screens[self.active_screen_name].grid(row=0, column=0, sticky="nsew")
        self.update_nav_button_highlight(self.active_screen_name)

        # Start inactivity timer
        self._schedule_inactivity_check()

        # Touch session on any mouse/keyboard event
        self.bind("<Motion>",  lambda e: SessionManager.touch(), add="+")
        self.bind("<KeyPress>", lambda e: SessionManager.touch(), add="+")

        self.after(100, self.trigger_startup_notification)
        self.after(2000, self._check_daily_backup)

    def logout(self):
        """Logs out the current user and returns to the login screen."""
        user = SessionManager.get_current_user()
        if user:
            self.audit_service.log_logout(user)

        SessionManager.end_session()

        # Hide main app shell
        self.sidebar_frame.grid_forget()
        self.container_frame.grid_forget()
        self.screens[self.active_screen_name].grid_forget()
        self.active_screen_name = "Dashboard"

        # Unbind inactivity events
        try:
            self.unbind("<Motion>")
            self.unbind("<KeyPress>")
        except Exception:
            pass

        self.show_login_screen()

    # ═══════════════════════════════════════════════════════════════════════
    #  INACTIVITY TIMER
    # ═══════════════════════════════════════════════════════════════════════

    def _schedule_inactivity_check(self):
        self._inactivity_job = self.after(INACTIVITY_CHECK_MS, self._check_inactivity)

    def _check_inactivity(self):
        if not SessionManager.is_logged_in():
            return
        if SessionManager.is_expired():
            user = SessionManager.get_current_user()
            self.audit_service.log_session_expired(user)
            self._lock_screen(user)
        else:
            self._schedule_inactivity_check()

    def _lock_screen(self, user):
        """Shows the lock screen without fully logging out."""
        self.sidebar_frame.grid_forget()
        self.container_frame.grid_forget()
        try:
            self.screens[self.active_screen_name].grid_forget()
        except Exception:
            pass

        SessionManager.lock_session()
        self.show_login_screen(locked_user=user)

    # ═══════════════════════════════════════════════════════════════════════
    #  ROLE-BASED NAV
    # ═══════════════════════════════════════════════════════════════════════

    def _apply_role_nav_visibility(self, user):
        """Shows/hides sidebar nav items based on user role."""
        # Import: Owner only
        import_btn = self.nav_buttons.get("Import")
        if import_btn:
            if user.has_permission(Permission.IMPORT_DATA):
                import_btn.grid()
            else:
                import_btn.grid_remove()

        # Settings: Owner only
        settings_btn = self.nav_buttons.get("Settings")
        if settings_btn:
            if user.has_permission(Permission.VIEW_SETTINGS):
                settings_btn.grid()
            else:
                settings_btn.grid_remove()

        # Users: Owner only
        users_btn = self.nav_buttons.get("Users")
        if users_btn:
            if user.has_permission(Permission.USER_MANAGEMENT):
                users_btn.grid()
            else:
                users_btn.grid_remove()

    def _update_user_widget(self, user):
        """Updates the bottom-of-sidebar user info widget."""
        self.user_name_lbl.configure(text=f"  {user.username}")
        self.user_role_lbl.configure(text=f"  {user.display_role()}")
        ll = user.last_login[:16] if user.last_login else "First login"
        self.user_login_lbl.configure(text=f"  Last: {ll}")

    # ═══════════════════════════════════════════════════════════════════════
    #  SCREEN ROUTING
    # ═══════════════════════════════════════════════════════════════════════

    def switch_screen(self, screen_name: str, **kwargs):
        """Role-aware view router."""
        if screen_name not in self.screens:
            return

        # Permission check for restricted screens
        user = SessionManager.get_current_user()
        RESTRICTED = {
            "Settings": Permission.VIEW_SETTINGS,
            "Import":   Permission.IMPORT_DATA,
            "Users":    Permission.USER_MANAGEMENT,
        }
        if screen_name in RESTRICTED and user:
            if not user.has_permission(RESTRICTED[screen_name]):
                from tkinter import messagebox
                messagebox.showwarning(
                    "Access Denied",
                    f"Your account does not have permission to access {screen_name}."
                )
                return

        # Touch session on navigation
        SessionManager.touch()

        self.screens[self.active_screen_name].grid_forget()

        if screen_name == "Ledger":
            cid = kwargs.get("customer_id")
            if cid:
                self.screens["Ledger"].load_customer(cid)
        elif screen_name == "Dashboard":
            self.screens["Dashboard"].refresh()
        elif screen_name == "Customers":
            self.screens["Customers"].refresh_list()
        elif screen_name == "New Entry":
            self.screens["New Entry"].refresh_customer_options()
            self.screens["New Entry"].set_date_to_now()
        elif screen_name == "Reports":
            self.screens["Reports"].refresh_customer_filters()
        elif screen_name == "Import":
            self.screens["Import"].refresh()
        elif screen_name == "Users":
            self.screens["Users"].refresh()

        self.active_screen_name = screen_name
        self.screens[self.active_screen_name].grid(row=0, column=0, sticky="nsew")
        self.update_nav_button_highlight(screen_name)

    def update_nav_button_highlight(self, screen_name: str):
        for name, btn in self.nav_buttons.items():
            is_active = (name == screen_name) or (name == "Customers" and screen_name == "Ledger")
            if is_active:
                btn.configure(fg_color=Theme.ACCENT, text_color=Theme.TEXT_WHITE)
            else:
                btn.configure(fg_color="transparent", text_color=Theme.TEXT_PRIMARY)

    # ═══════════════════════════════════════════════════════════════════════
    #  EXISTING CALLBACKS (unchanged logic, + audit hooks)
    # ═══════════════════════════════════════════════════════════════════════

    def get_business_info(self) -> dict:
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"name": "Jalajs Ledger Store", "address": "Market Road, Dehradun"}

    def on_database_reset(self):
        self.audit_service.log(AuditAction.BACKUP_RESTORED, "Database reset/restored via Settings")
        self.screens["Dashboard"].refresh()
        self.screens["Customers"].refresh_list()
        self.screens["New Entry"].refresh_customer_options()
        self.screens["New Entry"].reset_form()
        if self.active_screen_name == "Ledger":
            self.switch_screen("Customers")

    def on_import_complete(self, result):
        try:
            if isinstance(result, dict):
                count = result.get("imported", 0)
            elif hasattr(result, "imported"):
                count = result.imported
            else:
                count = "?"
            self.audit_service.log(AuditAction.IMPORT_COMPLETED, f"Import completed: {count} records")
            self.screens["Dashboard"].refresh()
            self.screens["Customers"].refresh_list()
            self.screens["New Entry"].refresh_customer_options()
            self.screens["Reports"].refresh_customer_filters()
        except Exception as e:
            print(f"[App] Post-import refresh error: {e}")

    def trigger_startup_notification(self):
        if getattr(self, "_is_closing", False):
            return
        settings = self.get_business_info()
        if not settings.get("startup_notification", True):
            return
        try:
            now = datetime.datetime.now()
            current_date = now.strftime("%Y-%m-%d")
            current_time = now.strftime("%H:%M:%S")
            customers = self.customer_service.list_customers()
            total_customers = len(customers)
            summary = self.report_service.get_financial_summary()
            total_credit = summary.get("total_credit", 0.0)
            total_debit  = summary.get("total_debit", 0.0) + summary.get("total_charges", 0.0)
            outstanding  = summary.get("net_change", 0.0)
            title = "Jalaj Ledger Started!"
            msg   = (
                f"Date: {current_date} | Time: {current_time}\n"
                f"Total Customers: {total_customers}\n"
                f"Debit: ₹{total_debit:,.2f} | Credit: ₹{total_credit:,.2f}\n"
                f"Outstanding: ₹{outstanding:,.2f}"
            )
            self.notification_service.send_notification(title, msg)
            if settings.get("whatsapp_delivery", False):
                import threading
                threading.Thread(
                    target=self.whatsapp_service.send_text_report,
                    args=(msg,),
                    daemon=True
                ).start()
        except Exception as e:
            print(f"[App] Startup notification error: {e}")

    def _check_daily_backup(self):
        try:
            self.backup_manager.trigger_daily_backup_if_needed()
        except Exception as e:
            print(f"[App] Daily backup check failed: {e}")

    def on_close(self):
        if getattr(self, "_is_closing", False):
            return
        self._is_closing = True

        # Log logout
        user = SessionManager.get_current_user()
        if user:
            try:
                self.audit_service.log_logout(user)
            except Exception:
                pass
        SessionManager.end_session()

        try:
            ok, msg = self.backup_manager.trigger_shutdown_backup()
            print(f"[App] Shutdown backup: {msg}")
        except Exception as be:
            print(f"[App] Shutdown backup error: {be}")

        try:
            now = datetime.datetime.now()
            current_date = now.strftime("%Y-%m-%d")
            close_time   = now.strftime("%H:%M:%S")
            today        = self.report_service.get_todays_summary()
            count        = today["count"]
            today_credit = today["total_credit"]
            today_debit  = today["total_debit"] + today["total_charges"]
            all_time     = self.report_service.get_financial_summary()
            outstanding  = all_time["net_change"]
            customers    = self.customer_service.list_customers()
            total_cust   = len(customers)
            start_dt     = f"{current_date} 00:00:00"
            end_dt       = f"{current_date} 23:59:59"
            todays_txns  = self.report_service.get_date_range_report(start_dt, end_dt)
            settings     = self.get_business_info()

            pdf_path = None
            if settings.get("generate_daily_report", True):
                pdf_summary = {
                    "date": current_date, "time": close_time,
                    "customer_count": total_cust,
                    "total_credit": today_credit, "total_debit": today_debit,
                    "outstanding_balance": outstanding
                }
                pdf_dir  = os.path.join("reports", current_date)
                os.makedirs(pdf_dir, exist_ok=True)
                pdf_path = os.path.join(pdf_dir, "daily_summary.pdf")
                self.export_service.export_daily_summary_pdf(pdf_summary, todays_txns, pdf_path)

            if settings.get("shutdown_notification", True):
                title = "Jalaj Ledger Closed"
                msg   = (
                    f"Closed: {close_time}\n"
                    f"Today's Txns: {count}\n"
                    f"Today's Dr: ₹{today_debit:,.2f} | Cr: ₹{today_credit:,.2f}\n"
                    f"Net Owed: ₹{outstanding:,.2f}"
                )
                self.notification_service.send_notification(title, msg)

            if settings.get("whatsapp_delivery", False) and pdf_path:
                try:
                    self.whatsapp_service.send_report_with_pdf(msg, pdf_path)
                except Exception:
                    pass

            email_body = (
                f"Daily Ledger Summary\n\nDate: {current_date}\n\n"
                f"Total Credit: ₹{today_credit:,.2f}\nTotal Debit: ₹{today_debit:,.2f}\n"
                f"Outstanding: ₹{outstanding:,.2f}"
            )
            try:
                self.email_service.send_email_report(
                    f"Daily Ledger Summary - {current_date}", email_body, pdf_path
                )
            except Exception:
                pass

        except Exception as e:
            print(f"[App] Shutdown error: {e}")
        finally:
            self.destroy()

    def on_theme_changed(self, new_theme: str):
        self.configure(fg_color=Theme.BG_PRIMARY)
        self.update_nav_button_highlight(self.active_screen_name)
        for name, screen in self.screens.items():
            if hasattr(screen, "refresh"):
                try:
                    screen.refresh()
                except Exception as e:
                    print(f"[App] Theme refresh error on {name}: {e}")
            elif name == "Customers" and hasattr(screen, "refresh_list"):
                try:
                    screen.refresh_list()
                except Exception:
                    pass


class StaffForcePasswordChangeDialog(ctk.CTkToplevel):
    """Forced modal dialog requiring Staff to set a new password before using the app."""

    def __init__(self, parent, user, auth_service, audit_service, on_success):
        super().__init__(parent)
        self.user = user
        self.auth_service = auth_service
        self.audit_service = audit_service
        self.on_success = on_success
        self._changed = False

        self.title("Password Change Required")
        w, h = 420, 360
        x = parent.winfo_x() + (parent.winfo_width()  - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.resizable(False, False)
        self.configure(fg_color=Theme.BG_SECONDARY)
        self.transient(parent)
        self.grab_set()

        # Handle window close (X button) to log out if they didn't change password
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        ctk.CTkLabel(
            self,
            text="Temporary Password Detected",
            font=Theme.FONT_SUBTITLE, text_color=Theme.DEBIT_RED
        ).pack(pady=(25, 6))

        ctk.CTkLabel(
            self,
            text="For security, you must set a new permanent password\nbefore you can access the system.",
            font=Theme.FONT_BODY, text_color=Theme.TEXT_SECONDARY,
            justify="center"
        ).pack(pady=(0, 20))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=40)
        form.columnconfigure(0, weight=1)

        # New Password
        ctk.CTkLabel(form, text="New Password", font=Theme.FONT_BODY_BOLD, anchor="w").grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.password_entry = ctk.CTkEntry(form, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS, show="•", placeholder_text="Enter new password", height=36)
        self.password_entry.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.password_entry.focus()

        # Confirm New Password
        ctk.CTkLabel(form, text="Confirm New Password", font=Theme.FONT_BODY_BOLD, anchor="w").grid(row=2, column=0, sticky="w", pady=(0, 2))
        self.confirm_pw_entry = ctk.CTkEntry(form, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS, show="•", placeholder_text="Confirm new password", height=36)
        self.confirm_pw_entry.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self.confirm_pw_entry.bind("<Return>", lambda e: self._submit())

        self.error_lbl = ctk.CTkLabel(self, text="", font=Theme.FONT_CAPTION, text_color=Theme.DEBIT_RED, wraplength=320)
        self.error_lbl.pack(pady=4)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=40, pady=(10, 15))

        self.cancel_btn = ctk.CTkButton(
            btn_row, text="Logout",
            fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            border_width=1, border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY, command=self._on_close
        )
        self.cancel_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))

        self.save_btn = ctk.CTkButton(
            btn_row, text="Update Password",
            fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER,
            command=self._submit
        )
        self.save_btn.pack(side="right", expand=True, fill="x")

    def _submit(self):
        pw = self.password_entry.get()
        pwc = self.confirm_pw_entry.get()

        if not pw or not pwc:
            self.error_lbl.configure(text="Please fill both password fields.")
            return

        if pw != pwc:
            self.error_lbl.configure(text="Passwords do not match.")
            return

        # Validate complexity
        ok, msg = self.auth_service._validate_new_password(pw)
        if not ok:
            self.error_lbl.configure(text=msg)
            return

        # Update in database
        from ledger_app.services.auth_service import _hash_secret
        salt_hex, hash_hex = _hash_secret(pw)
        self.auth_service.repo.update_password(self.user.id, hash_hex, salt_hex)
        
        # Reset must_change to 0
        self.auth_service.repo.set_must_change(self.user.id, False)

        # Log password reset action
        if self.audit_service:
            self.audit_service.log_as("PASSWORD_RESET", f"Staff password updated from temporary password for user '{self.user.username}'.", self.user.id, self.user.username)

        self._changed = True
        from tkinter import messagebox
        messagebox.showinfo("Success", "Password updated successfully. Access granted.")
        self.on_success()
        self.destroy()

    def _on_close(self):
        if not self._changed:
            self.destroy()
            # Callback to trigger logout on parent App
            self.on_success(force_logout=True)
