"""
login_screen.py
---------------
Multi-user login screen with:
  - Username + Password authentication
  - Optional Quick PIN unlock (after first password login)
  - Remember-username feature
  - Password strength meter for first-run setup
  - Branded header from settings.json
"""

import json
import os
import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, Optional

from ledger_app.ui.theme import Theme
from ledger_app.ui.theme_manager import ThemeManager


SETTINGS_FILE = "settings.json"


def _load_setting(key: str, default=None):
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get(key, default)
        except Exception:
            pass
    return default


def _save_setting(key: str, value) -> None:
    data = {}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    data[key] = value
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[LoginScreen] Failed to save setting: {e}")


class LoginScreen(ctk.CTkFrame):
    """
    Full-screen multi-user login frame.

    on_success(user) is called with the authenticated User object
    once credentials are verified.
    """

    def __init__(self, parent, on_success: Callable, auth_service=None, audit_service=None):
        super().__init__(parent, fg_color="transparent")
        self.on_success     = on_success
        self.auth_service   = auth_service
        self.audit_service  = audit_service
        self._show_pin_panel = False
        self._authenticated_user = None   # set after password login, enables PIN

        # Full-screen grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Background canvas
        self.bg = ctk.CTkFrame(self, fg_color=Theme.BG_PRIMARY, corner_radius=0)
        self.bg.grid(row=0, column=0, sticky="nsew")
        self.bg.grid_columnconfigure(0, weight=1)
        self.bg.grid_columnconfigure(1, weight=1)
        self.bg.grid_rowconfigure(0, weight=1)

        # Left decorative branding panel
        self._build_brand_panel()
        # Right auth card
        self._build_auth_card()

    # ═══════════════════════════════════════════════════════════════════
    #  BRAND PANEL (left half)
    # ═══════════════════════════════════════════════════════════════════

    def _build_brand_panel(self):
        brand = ctk.CTkFrame(
            self.bg,
            fg_color=Theme.BG_SIDEBAR,
            corner_radius=0,
            border_width=0
        )
        brand.grid(row=0, column=0, sticky="nsew")
        brand.grid_rowconfigure(0, weight=1)
        brand.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(brand, fg_color="transparent")
        inner.grid(row=0, column=0)

        business_name = _load_setting("business_name", "JALAJ LEDGER")

        ctk.CTkLabel(
            inner, text="📒",
            font=(Theme.FONT_FAMILY, 72),
            text_color=Theme.ACCENT
        ).pack(pady=(0, 15))

        ctk.CTkLabel(
            inner,
            text=business_name.upper(),
            font=(Theme.FONT_FAMILY, 26, "bold"),
            text_color=Theme.ACCENT
        ).pack()

        ctk.CTkLabel(
            inner,
            text="Ledger Management System",
            font=(Theme.FONT_FAMILY, 13),
            text_color=Theme.TEXT_SECONDARY
        ).pack(pady=(4, 0))

        # Feature pills
        features = ["📊 Analytics", "👤 Multi-User", "🔒 Secure", "📈 Reports"]
        pill_frame = ctk.CTkFrame(inner, fg_color="transparent")
        pill_frame.pack(pady=(30, 0))

        for i, feat in enumerate(features):
            ctk.CTkLabel(
                pill_frame,
                text=feat,
                font=(Theme.FONT_FAMILY, 10),
                text_color=Theme.TEXT_SECONDARY,
                fg_color=Theme.BG_TERTIARY,
                corner_radius=12,
                padx=10, pady=5
            ).grid(row=i // 2, column=i % 2, padx=6, pady=4)

    # ═══════════════════════════════════════════════════════════════════
    #  AUTH CARD (right half)
    # ═══════════════════════════════════════════════════════════════════

    def _build_auth_card(self):
        right = ctk.CTkFrame(self.bg, fg_color=Theme.BG_SECONDARY, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)

        # Centered card container
        self.card = ctk.CTkFrame(
            right,
            fg_color=Theme.BG_SECONDARY,
            corner_radius=20,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR,
            width=400, height=520
        )
        self.card.grid(row=0, column=0, padx=50, pady=50)
        self.card.grid_propagate(False)
        self.card.grid_columnconfigure(0, weight=1)

        self._build_password_panel()

    def _build_password_panel(self):
        """Main username + password login form."""
        for w in self.card.winfo_children():
            w.destroy()

        # Title
        ctk.CTkLabel(
            self.card,
            text="Welcome Back",
            font=(Theme.FONT_FAMILY, 22, "bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(pady=(40, 4))

        ctk.CTkLabel(
            self.card,
            text="Sign in to continue",
            font=Theme.FONT_BODY,
            text_color=Theme.TEXT_SECONDARY
        ).pack(pady=(0, 30))

        # Form fields container
        form = ctk.CTkFrame(self.card, fg_color="transparent")
        form.pack(fill="x", padx=40)
        form.columnconfigure(0, weight=1)

        # Username
        ctk.CTkLabel(
            form, text="Username",
            font=Theme.FONT_BODY_BOLD, text_color=Theme.TEXT_PRIMARY, anchor="w"
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.username_entry = ctk.CTkEntry(
            form,
            font=Theme.FONT_BODY,
            corner_radius=Theme.CORNER_RADIUS,
            height=38,
            placeholder_text="Enter your username"
        )
        self.username_entry.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        self.username_entry.bind("<Return>", lambda e: self.password_entry.focus())

        # Restore remembered username
        remembered = _load_setting("remembered_username", "")
        if remembered:
            self.username_entry.insert(0, remembered)

        # Password
        ctk.CTkLabel(
            form, text="Password",
            font=Theme.FONT_BODY_BOLD, text_color=Theme.TEXT_PRIMARY, anchor="w"
        ).grid(row=2, column=0, sticky="w", pady=(0, 4))

        pw_row = ctk.CTkFrame(form, fg_color="transparent")
        pw_row.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        pw_row.columnconfigure(0, weight=1)

        self.password_entry = ctk.CTkEntry(
            pw_row,
            font=Theme.FONT_BODY,
            corner_radius=Theme.CORNER_RADIUS,
            height=38,
            show="•",
            placeholder_text="Enter your password"
        )
        self.password_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.password_entry.bind("<Return>", lambda e: self._do_login())

        self._pw_visible = False
        eye_btn = ctk.CTkButton(
            pw_row, text="👁", width=38, height=38,
            fg_color=Theme.BG_TERTIARY, hover_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY, corner_radius=Theme.CORNER_RADIUS,
            command=self._toggle_pw_visibility
        )
        eye_btn.grid(row=0, column=1)
        self._eye_btn = eye_btn

        # Remember username checkbox
        self._remember_var = ctk.BooleanVar(value=bool(remembered))
        ctk.CTkCheckBox(
            form,
            text="Remember username",
            variable=self._remember_var,
            font=Theme.FONT_CAPTION,
            text_color=Theme.TEXT_SECONDARY,
            checkmark_color=Theme.ACCENT,
            fg_color=Theme.ACCENT,
            border_color=Theme.BORDER_COLOR,
            hover_color=Theme.BG_TERTIARY
        ).grid(row=4, column=0, sticky="w", pady=(4, 0))

        # Error label
        self.error_lbl = ctk.CTkLabel(
            self.card, text="",
            font=Theme.FONT_CAPTION,
            text_color=Theme.DEBIT_RED,
            wraplength=320
        )
        self.error_lbl.pack(pady=(14, 0))

        # Login button
        self.login_btn = ctk.CTkButton(
            self.card,
            text="Sign In",
            font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.ACCENT,
            hover_color=Theme.ACCENT_HOVER,
            corner_radius=Theme.CORNER_RADIUS,
            height=42,
            command=self._do_login
        )
        self.login_btn.pack(fill="x", padx=40, pady=(18, 10))

        # PIN quick-unlock link (shown only if user has a PIN set and already logged in once)
        if self._authenticated_user and self.auth_service and \
                self.auth_service.has_pin(self._authenticated_user.id):
            pin_link = ctk.CTkButton(
                self.card,
                text="Use PIN instead →",
                font=Theme.FONT_CAPTION,
                fg_color="transparent",
                hover_color=Theme.BG_TERTIARY,
                text_color=Theme.ACCENT,
                command=self._build_pin_panel
            )
            pin_link.pack()

        # Forgot Password link
        self.forgot_pw_btn = ctk.CTkButton(
            self.card,
            text="Forgot Password?",
            font=Theme.FONT_CAPTION,
            fg_color="transparent",
            hover_color=Theme.BG_TERTIARY,
            text_color=Theme.ACCENT,
            command=self._forgot_password_flow
        )
        self.forgot_pw_btn.pack(pady=(4, 0))

        # Version footer
        ctk.CTkLabel(
            self.card,
            text="Jalaj Ledger v2.0 · Multi-User Edition",
            font=(Theme.FONT_FAMILY, 9),
            text_color=Theme.TEXT_SECONDARY
        ).pack(side="bottom", pady=12)

        self.after(120, lambda: self.username_entry.focus() if not _load_setting("remembered_username") else self.password_entry.focus())

    def _build_pin_panel(self):
        """Quick PIN unlock panel (4–6 digit keypad style)."""
        for w in self.card.winfo_children():
            w.destroy()

        ctk.CTkLabel(
            self.card,
            text=f"Hello, {self._authenticated_user.username} 👋",
            font=(Theme.FONT_FAMILY, 20, "bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(pady=(45, 4))

        ctk.CTkLabel(
            self.card,
            text="Enter your PIN to unlock",
            font=Theme.FONT_BODY,
            text_color=Theme.TEXT_SECONDARY
        ).pack(pady=(0, 24))

        # PIN dot display
        self._pin_value = ""
        self._pin_dots_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self._pin_dots_frame.pack(pady=(0, 12))
        self._pin_dots = []
        for _ in range(6):
            dot = ctk.CTkLabel(
                self._pin_dots_frame,
                text="○",
                font=(Theme.FONT_FAMILY, 22),
                text_color=Theme.TEXT_SECONDARY,
                width=28
            )
            dot.pack(side="left", padx=4)
            self._pin_dots.append(dot)

        # Numpad grid
        pad_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        pad_frame.pack(pady=4)
        keys = [("1","2","3"), ("4","5","6"), ("7","8","9"), ("←","0","✓")]
        for r, row in enumerate(keys):
            for c, key in enumerate(row):
                is_confirm = key == "✓"
                is_back    = key == "←"
                btn = ctk.CTkButton(
                    pad_frame,
                    text=key,
                    width=70, height=48,
                    font=(Theme.FONT_FAMILY, 18, "bold"),
                    corner_radius=10,
                    fg_color=Theme.ACCENT if is_confirm else Theme.BG_TERTIARY,
                    hover_color=Theme.ACCENT_HOVER if is_confirm else Theme.BORDER_COLOR,
                    text_color=Theme.TEXT_WHITE if is_confirm else Theme.TEXT_PRIMARY,
                    command=lambda k=key: self._pin_key_press(k)
                )
                btn.grid(row=r, column=c, padx=5, pady=5)

        # Error label
        self.error_lbl = ctk.CTkLabel(
            self.card, text="",
            font=Theme.FONT_CAPTION, text_color=Theme.DEBIT_RED
        )
        self.error_lbl.pack(pady=(8, 0))

        # Back to password link
        ctk.CTkButton(
            self.card,
            text="← Use password instead",
            font=Theme.FONT_CAPTION,
            fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            text_color=Theme.TEXT_SECONDARY,
            command=self._build_password_panel
        ).pack(pady=(4, 0))

    def _pin_key_press(self, key: str):
        if key == "←":
            self._pin_value = self._pin_value[:-1]
        elif key == "✓":
            self._verify_pin()
            return
        elif key.isdigit() and len(self._pin_value) < 6:
            self._pin_value += key

        # Update dot display
        for i, dot in enumerate(self._pin_dots):
            dot.configure(text="●" if i < len(self._pin_value) else "○",
                          text_color=Theme.ACCENT if i < len(self._pin_value) else Theme.TEXT_SECONDARY)

    def _verify_pin(self):
        if not self._pin_value:
            self.error_lbl.configure(text="Enter your PIN first.")
            return
        if len(self._pin_value) < 4:
            self.error_lbl.configure(text="PIN must be at least 4 digits.")
            return

        if self.auth_service and self.auth_service.verify_pin(
            self._authenticated_user.id, self._pin_value
        ):
            self._complete_login(self._authenticated_user)
        else:
            self.error_lbl.configure(text="Incorrect PIN. Try again.")
            self._pin_value = ""
            for dot in self._pin_dots:
                dot.configure(text="○", text_color=Theme.TEXT_SECONDARY)

    # ═══════════════════════════════════════════════════════════════════
    #  ACTIONS
    # ═══════════════════════════════════════════════════════════════════

    def _toggle_pw_visibility(self):
        self._pw_visible = not self._pw_visible
        self.password_entry.configure(show="" if self._pw_visible else "•")
        self._eye_btn.configure(text="👁‍🗨" if self._pw_visible else "👁")

    def _do_login(self):
        """Validates credentials and proceeds to the application."""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            self.error_lbl.configure(text="Both username and password are required.")
            return

        self.login_btn.configure(state="disabled", text="Signing in…")
        self.after(50, lambda: self._process_login(username, password))

    def _process_login(self, username: str, password: str):
        # Handle case where auth_service is not yet wired (legacy/test mode)
        if self.auth_service is None:
            self._complete_login(None)
            return

        user, error = self.auth_service.login(username, password)
        self.login_btn.configure(state="normal", text="Sign In")

        if user:
            self._authenticated_user = user

            # Handle remember username
            if self._remember_var.get():
                _save_setting("remembered_username", username)
            else:
                _save_setting("remembered_username", "")

            if self.audit_service:
                self.audit_service.log_login(user)

            self._complete_login(user)
        else:
            self.error_lbl.configure(text=error or "Login failed.")
            self.password_entry.delete(0, "end")
            self.password_entry.focus()

    def _complete_login(self, user):
        """Calls on_success with the authenticated user."""
        self.on_success(user)

    # ═══════════════════════════════════════════════════════════════════
    #  LOCK SCREEN (session expired)
    # ═══════════════════════════════════════════════════════════════════

    def rebuild_as_lock_screen(self, locked_user):
        """Transforms the login card into a re-authentication lock screen."""
        self._authenticated_user = locked_user
        for w in self.card.winfo_children():
            w.destroy()

        ctk.CTkLabel(
            self.card, text="🔒  Session Locked",
            font=(Theme.FONT_FAMILY, 20, "bold"),
            text_color=Theme.DEBIT_RED
        ).pack(pady=(40, 4))

        ctk.CTkLabel(
            self.card,
            text=f"Logged in as: {locked_user.username}\nSession expired due to inactivity.",
            font=Theme.FONT_BODY,
            text_color=Theme.TEXT_SECONDARY,
            justify="center"
        ).pack(pady=(0, 24))

        form = ctk.CTkFrame(self.card, fg_color="transparent")
        form.pack(fill="x", padx=40)
        form.columnconfigure(0, weight=1)

        ctk.CTkLabel(form, text="Password", font=Theme.FONT_BODY_BOLD,
                     text_color=Theme.TEXT_PRIMARY, anchor="w").grid(row=0, column=0, sticky="w", pady=(0,4))

        self.password_entry = ctk.CTkEntry(
            form, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS,
            height=38, show="•", placeholder_text="Re-enter your password"
        )
        self.password_entry.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.password_entry.bind("<Return>", lambda e: self._do_lock_verify(locked_user))

        self.error_lbl = ctk.CTkLabel(
            self.card, text="", font=Theme.FONT_CAPTION, text_color=Theme.DEBIT_RED
        )
        self.error_lbl.pack(pady=(8, 0))

        ctk.CTkButton(
            self.card, text="Unlock",
            font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER,
            corner_radius=Theme.CORNER_RADIUS, height=42,
            command=lambda: self._do_lock_verify(locked_user)
        ).pack(fill="x", padx=40, pady=(14, 8))

        ctk.CTkButton(
            self.card, text="Switch Account",
            font=Theme.FONT_CAPTION,
            fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            text_color=Theme.TEXT_SECONDARY,
            command=self._build_password_panel
        ).pack()

        self.after(100, lambda: self.password_entry.focus())

    def _do_lock_verify(self, locked_user):
        password = self.password_entry.get()
        if not password:
            self.error_lbl.configure(text="Password is required.")
            return
        if self.auth_service:
            user, err = self.auth_service.login(locked_user.username, password)
            if user:
                self._complete_login(user)
            else:
                self.error_lbl.configure(text=err or "Incorrect password.")
                self.password_entry.delete(0, "end")
        else:
            self._complete_login(locked_user)

    def _forgot_password_flow(self):
        """Launches the Forgot Password wizard dialog."""
        ForgotPasswordDialog(self, self.auth_service, self.audit_service)


class ForgotPasswordDialog(ctk.CTkToplevel):
    """Wizard-style modal dialog for Owner account recovery via Email OTP."""

    def __init__(self, parent, auth_service, audit_service):
        super().__init__(parent)
        self.auth_service = auth_service
        self.audit_service = audit_service
        self.user_repo = auth_service.repo if auth_service else None
        
        self.title("Account Recovery")
        w, h = 420, 380
        x = parent.winfo_x() + (parent.winfo_width()  - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.resizable(False, False)
        self.configure(fg_color=Theme.BG_SECONDARY)
        self.transient(parent)
        self.grab_set()

        self.username = ""
        self.otp = ""

        # Step tracking: 1=username, 2=OTP verification, 3=new password
        self.current_step = 1
        self._build_ui()

    def _build_ui(self):
        # Clear dialog
        for widget in self.winfo_children():
            widget.destroy()

        if self.current_step == 1:
            self._step_username()
        elif self.current_step == 2:
            self._step_otp()
        elif self.current_step == 3:
            self._step_password()

    def _step_username(self):
        ctk.CTkLabel(
            self,
            text="Forgot Password",
            font=Theme.FONT_SUBTITLE, text_color=Theme.TEXT_PRIMARY
        ).pack(pady=(30, 8))

        ctk.CTkLabel(
            self,
            text="Enter your username to recover your account.",
            font=Theme.FONT_BODY, text_color=Theme.TEXT_SECONDARY
        ).pack(pady=(0, 25))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=40)
        form.columnconfigure(0, weight=1)

        ctk.CTkLabel(form, text="Username", font=Theme.FONT_BODY_BOLD, anchor="w").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.username_entry = ctk.CTkEntry(form, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS, height=36, placeholder_text="Enter username")
        self.username_entry.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        self.username_entry.focus()
        self.username_entry.bind("<Return>", lambda e: self._submit_username())

        self.error_lbl = ctk.CTkLabel(self, text="", font=Theme.FONT_CAPTION, text_color=Theme.DEBIT_RED)
        self.error_lbl.pack(pady=5)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=40, pady=(15, 20))

        ctk.CTkButton(
            btn_row, text="Cancel",
            fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            border_width=1, border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY, command=self.destroy
        ).pack(side="left", expand=True, fill="x", padx=(0, 8))

        self.next_btn = ctk.CTkButton(
            btn_row, text="Continue",
            fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER,
            command=self._submit_username
        )
        self.next_btn.pack(side="right", expand=True, fill="x")

    def _submit_username(self):
        username = self.username_entry.get().strip()
        if not username:
            self.error_lbl.configure(text="Username is required.")
            return

        # Check if email recovery is enabled globally in settings
        email_recovery_enabled = _load_setting("email_recovery_enabled", False)
        if not email_recovery_enabled:
            self.error_lbl.configure(text="Email recovery is disabled in Settings.")
            return

        if not self.user_repo:
            self.error_lbl.configure(text="Auth system not initialized.")
            return

        # Check lockout
        from ledger_app.services.otp_service import OtpService
        is_locked, lock_msg = OtpService.is_locked_out(username, self.user_repo)
        if is_locked:
            self.error_lbl.configure(text=lock_msg)
            return

        recovery_info = self.user_repo.get_recovery_info(username)
        if not recovery_info:
            self.error_lbl.configure(text="User not found.")
            return

        # Only Owner account can use recovery
        if recovery_info["role"] != "owner":
            self.error_lbl.configure(text="Staff accounts cannot use self-recovery.\nPlease contact the Owner.")
            return

        recovery_email = recovery_info.get("recovery_email")
        if not recovery_email:
            self.error_lbl.configure(text="No recovery email set for Owner.\nPlease contact the administrator.")
            return

        self.username = username
        self.recovery_email = recovery_email
        
        # Trigger sending OTP
        self.next_btn.configure(state="disabled", text="Sending OTP...")
        self.update()

        import threading
        def send_task():
            try:
                otp = OtpService.generate_otp(username)
                
                from ledger_app.services.email_service import EmailService
                from ledger_app.services.email_recovery_service import EmailRecoveryService
                email_svc = EmailService()
                
                success = EmailRecoveryService.send_otp_email(recovery_email, otp, email_svc)
                if success:
                    # Update database with last recovery timestamp
                    import datetime
                    self.user_repo.set_last_recovery_request(username, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    
                    # Log audit action
                    if self.audit_service:
                        self.audit_service.log_as("OTP_GENERATED", f"OTP generated for recovery of user '{username}'.", recovery_info["id"], username)
                        self.audit_service.log_as("OTP_SENT", f"OTP sent to email '{recovery_email}' for recovery of user '{username}'.", recovery_info["id"], username)
                    
                    def ok():
                        self.current_step = 2
                        self._build_ui()
                    self.after(0, ok)
                else:
                    def err():
                        self.next_btn.configure(state="normal", text="Continue")
                        self.error_lbl.configure(text="Failed to send email. Check SMTP settings.")
                    self.after(0, err)
            except Exception as e:
                def fatal(msg=str(e)):
                    self.next_btn.configure(state="normal", text="Continue")
                    self.error_lbl.configure(text=f"Error: {msg}")
                self.after(0, fatal)

        threading.Thread(target=send_task, daemon=True).start()

    def _step_otp(self):
        ctk.CTkLabel(
            self,
            text="Verify OTP",
            font=Theme.FONT_SUBTITLE, text_color=Theme.TEXT_PRIMARY
        ).pack(pady=(30, 8))

        # Mask email address (e.g. j****l@gmail.com)
        parts = self.recovery_email.split("@")
        masked = parts[0][0] + "****" + parts[0][-1] + "@" + parts[1] if len(parts[0]) > 2 else "****@" + parts[1]
        
        ctk.CTkLabel(
            self,
            text=f"Enter the 6-digit OTP sent to {masked}.",
            font=Theme.FONT_BODY, text_color=Theme.TEXT_SECONDARY
        ).pack(pady=(0, 20))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=40)
        form.columnconfigure(0, weight=1)

        ctk.CTkLabel(form, text="OTP Verification Code", font=Theme.FONT_BODY_BOLD, anchor="w").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.otp_entry = ctk.CTkEntry(form, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS, height=36, placeholder_text="Enter 6-digit OTP")
        self.otp_entry.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        self.otp_entry.focus()
        self.otp_entry.bind("<Return>", lambda e: self._submit_otp())

        self.error_lbl = ctk.CTkLabel(self, text="", font=Theme.FONT_CAPTION, text_color=Theme.DEBIT_RED)
        self.error_lbl.pack(pady=5)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=40, pady=(15, 20))

        ctk.CTkButton(
            btn_row, text="Back",
            fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            border_width=1, border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY, command=lambda: self._go_back()
        ).pack(side="left", expand=True, fill="x", padx=(0, 8))

        self.verify_btn = ctk.CTkButton(
            btn_row, text="Verify",
            fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER,
            command=self._submit_otp
        )
        self.verify_btn.pack(side="right", expand=True, fill="x")

    def _go_back(self):
        from ledger_app.services.otp_service import OtpService
        OtpService.clear_otp(self.username)
        self.current_step = 1
        self._build_ui()

    def _submit_otp(self):
        otp_cand = self.otp_entry.get().strip()
        if not otp_cand:
            self.error_lbl.configure(text="Please enter OTP.")
            return

        from ledger_app.services.otp_service import OtpService
        success, msg = OtpService.verify_otp(self.username, otp_cand, self.user_repo)
        
        info = self.user_repo.get_recovery_info(self.username)
        
        if success:
            if self.audit_service:
                self.audit_service.log_as("OTP_VERIFIED", f"OTP verified successfully for recovery of user '{self.username}'.", info["id"], self.username)
            self.current_step = 3
            self._build_ui()
        else:
            if self.audit_service:
                # Get IP/Platform details for Failed Attempt audit log
                import socket
                import platform
                device_info = f"Host: {socket.gethostname()}, OS: {platform.system()} {platform.release()}"
                self.audit_service.log_as("FAILED_ATTEMPTS", f"Failed OTP attempt for user '{self.username}'. {device_info}", info["id"], self.username)
            
            # Recheck if locked out after this failure
            is_locked, lock_msg = OtpService.is_locked_out(self.username, self.user_repo)
            if is_locked:
                self.error_lbl.configure(text=lock_msg)
                self.verify_btn.configure(state="disabled")
            else:
                self.error_lbl.configure(text=msg)

    def _step_password(self):
        ctk.CTkLabel(
            self,
            text="Reset Password",
            font=Theme.FONT_SUBTITLE, text_color=Theme.TEXT_PRIMARY
        ).pack(pady=(20, 8))

        ctk.CTkLabel(
            self,
            text="Configure a strong enterprise-ready password.",
            font=Theme.FONT_BODY, text_color=Theme.TEXT_SECONDARY
        ).pack(pady=(0, 15))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=40)
        form.columnconfigure(0, weight=1)

        # Password
        ctk.CTkLabel(form, text="New Password", font=Theme.FONT_BODY_BOLD, anchor="w").grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.password_entry = ctk.CTkEntry(form, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS, show="•", placeholder_text="Enter new password")
        self.password_entry.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.password_entry.focus()

        # Confirm Password
        ctk.CTkLabel(form, text="Confirm New Password", font=Theme.FONT_BODY_BOLD, anchor="w").grid(row=2, column=0, sticky="w", pady=(0, 2))
        self.confirm_pw_entry = ctk.CTkEntry(form, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS, show="•", placeholder_text="Confirm new password")
        self.confirm_pw_entry.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self.confirm_pw_entry.bind("<Return>", lambda e: self._submit_password())

        self.error_lbl = ctk.CTkLabel(self, text="", font=Theme.FONT_CAPTION, text_color=Theme.DEBIT_RED, wraplength=320)
        self.error_lbl.pack(pady=2)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=40, pady=(10, 15))

        self.reset_btn = ctk.CTkButton(
            btn_row, text="Update Password",
            fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER,
            command=self._submit_password
        )
        self.reset_btn.pack(fill="x")

    def _submit_password(self):
        pw = self.password_entry.get()
        pwc = self.confirm_pw_entry.get()

        if not pw or not pwc:
            self.error_lbl.configure(text="Please fill both password fields.")
            return

        if pw != pwc:
            self.error_lbl.configure(text="Passwords do not match.")
            return

        # Validate complexity using AuthService validation
        ok, msg = self.auth_service._validate_new_password(pw)
        if not ok:
            self.error_lbl.configure(text=msg)
            return

        info = self.user_repo.get_recovery_info(self.username)
        if not info:
            self.error_lbl.configure(text="User not found.")
            return

        # Reset password
        from ledger_app.services.auth_service import _hash_secret
        salt_hex, hash_hex = _hash_secret(pw)
        self.user_repo.update_password(info["id"], hash_hex, salt_hex)
        
        # Clear temporary must_change flag for owner just in case
        self.user_repo.set_must_change(info["id"], False)
        self.user_repo.reset_otp_attempts(self.username)

        # Log password reset action
        if self.audit_service:
            self.audit_service.log_as("PASSWORD_RESET", f"Password successfully recovered/reset for user '{self.username}'.", info["id"], self.username)

        messagebox.showinfo("Success", "Password updated successfully. You can now log in.")
        self.destroy()
