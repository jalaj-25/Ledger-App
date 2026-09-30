"""
user_management.py
------------------
Owner-only screen for managing application user accounts.
Features:
  - User list with role badge, status, last login, and action buttons
  - Add User dialog (username, password, role)
  - Edit username / role
  - Reset Password / Reset PIN
  - Enable / Disable
  - Delete (with confirmation)
  - User count badge (N / 10)
  - Audit Log viewer tab
"""

import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, Optional
from ledger_app.ui.theme import Theme
from ledger_app.models.user import ROLES, ROLE_OWNER, ROLE_STAFF, MAX_USERS
from ledger_app.services.user_management_service import UserManagementService
from ledger_app.services.audit_service import AuditService, AuditAction
from ledger_app.services.session_manager import SessionManager


# ── Role badge colours ──────────────────────────────────────────────────────

ROLE_COLORS = {
    ROLE_OWNER: ("#F59E0B", "#FCD34D"),
    ROLE_STAFF: ("#0EA5E9", "#38BDF8"),
}


def _role_color(role: str) -> str:
    return ROLE_COLORS.get(role, ROLE_COLORS[ROLE_STAFF])[1]


# ── Add / Edit User Dialog ──────────────────────────────────────────────────

class UserFormDialog(ctk.CTkToplevel):
    """Modal dialog for creating or editing a user."""

    def __init__(
        self, parent,
        user_mgmt_service: UserManagementService,
        audit_service: AuditService,
        on_success: Callable,
        user_id: Optional[int] = None,
        username: str = "",
        role: str = ROLE_STAFF
    ):
        super().__init__(parent)
        self.svc          = user_mgmt_service
        self.audit        = audit_service
        self.on_success   = on_success
        self.user_id      = user_id
        self.is_edit      = user_id is not None

        self.title("Edit User" if self.is_edit else "Add New User")
        w, h = 420, 440 if not self.is_edit else 360
        x = parent.winfo_x() + (parent.winfo_width()  - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.resizable(False, False)
        self.configure(fg_color=Theme.BG_SECONDARY)
        self.transient(parent)
        self.grab_set()

        ctk.CTkLabel(
            self,
            text="Edit User Account" if self.is_edit else "Create New User",
            font=Theme.FONT_SUBTITLE, text_color=Theme.TEXT_PRIMARY
        ).pack(pady=(24, 16))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=36)
        form.columnconfigure(1, weight=1)

        row = 0

        # Username
        ctk.CTkLabel(form, text="Username *", font=Theme.FONT_BODY_BOLD).grid(row=row, column=0, sticky="w", pady=10)
        self.username_entry = ctk.CTkEntry(form, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS)
        self.username_entry.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=10)
        if username:
            self.username_entry.insert(0, username)
        row += 1

        # Role
        ctk.CTkLabel(form, text="Role *", font=Theme.FONT_BODY_BOLD).grid(row=row, column=0, sticky="w", pady=10)
        self.role_var = ctk.StringVar(value=role)
        self.role_menu = ctk.CTkOptionMenu(
            form, values=["owner", "staff"],
            variable=self.role_var,
            font=Theme.FONT_BODY,
            corner_radius=Theme.CORNER_RADIUS,
            fg_color=Theme.BG_TERTIARY,
            button_color=Theme.BG_TERTIARY,
            button_hover_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY
        )
        self.role_menu.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=10)
        row += 1

        # Password (only for new users)
        if not self.is_edit:
            ctk.CTkLabel(form, text="Password *", font=Theme.FONT_BODY_BOLD).grid(row=row, column=0, sticky="w", pady=10)
            self.pw_entry = ctk.CTkEntry(
                form, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS,
                show="•", placeholder_text="Min. 6 characters"
            )
            self.pw_entry.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=10)
            row += 1

            ctk.CTkLabel(form, text="Confirm *", font=Theme.FONT_BODY_BOLD).grid(row=row, column=0, sticky="w", pady=10)
            self.pw_confirm_entry = ctk.CTkEntry(
                form, font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS,
                show="•", placeholder_text="Re-enter password"
            )
            self.pw_confirm_entry.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=10)
            row += 1

        self.error_lbl = ctk.CTkLabel(
            self, text="", font=Theme.FONT_CAPTION, text_color=Theme.DEBIT_RED
        )
        self.error_lbl.pack(pady=(8, 0))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=36, pady=18)

        ctk.CTkButton(
            btn_row, text="Cancel",
            fg_color="transparent", hover_color=Theme.BG_TERTIARY,
            border_width=1, border_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY, command=self.destroy
        ).pack(side="left", expand=True, fill="x", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="Save" if self.is_edit else "Create User",
            fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER,
            command=self._save
        ).pack(side="right", expand=True, fill="x")

    def _save(self):
        uname = self.username_entry.get().strip()
        role  = self.role_var.get()
        curr  = SessionManager.get_current_user()

        if self.is_edit:
            ok, msg = self.svc.update_username(self.user_id, uname, curr.id)
            if ok:
                self.svc.update_role(self.user_id, role, curr.id)
                self.audit.log(AuditAction.USER_UPDATED, f"User ID {self.user_id} → username='{uname}', role='{role}'")
                self.on_success()
                self.destroy()
            else:
                self.error_lbl.configure(text=msg)
        else:
            pw  = self.pw_entry.get()
            pwc = self.pw_confirm_entry.get()
            if pw != pwc:
                self.error_lbl.configure(text="Passwords do not match.")
                return
            ok, msg = self.svc.create_user(uname, pw, role)
            if ok:
                self.audit.log(AuditAction.USER_CREATED, f"Created user '{uname}' with role '{role}'")
                self.on_success()
                self.destroy()
            else:
                self.error_lbl.configure(text=msg)


class ResetPasswordDialog(ctk.CTkToplevel):
    """Dialog for owner to reset another user's password."""

    def __init__(self, parent, svc: UserManagementService, audit: AuditService,
                 user_id: int, username: str, on_success: Callable):
        super().__init__(parent)
        self.svc = svc; self.audit = audit
        self.user_id = user_id; self.on_success = on_success

        self.title(f"Reset Password — {username}")
        w, h = 400, 300
        x = parent.winfo_x() + (parent.winfo_width()  - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.resizable(False, False)
        self.configure(fg_color=Theme.BG_SECONDARY)
        self.transient(parent); self.grab_set()

        ctk.CTkLabel(self, text=f"Reset Password\n{username}",
                     font=Theme.FONT_SUBTITLE, text_color=Theme.TEXT_PRIMARY,
                     justify="center").pack(pady=(24, 16))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=36)
        form.columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text="New Password", font=Theme.FONT_BODY_BOLD).grid(row=0, column=0, sticky="w", pady=10)
        self.pw_entry = ctk.CTkEntry(form, show="•", font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS)
        self.pw_entry.grid(row=0, column=1, sticky="ew", padx=(10,0), pady=10)

        ctk.CTkLabel(form, text="Confirm", font=Theme.FONT_BODY_BOLD).grid(row=1, column=0, sticky="w", pady=10)
        self.pw2_entry = ctk.CTkEntry(form, show="•", font=Theme.FONT_BODY, corner_radius=Theme.CORNER_RADIUS)
        self.pw2_entry.grid(row=1, column=1, sticky="ew", padx=(10,0), pady=10)

        self.err = ctk.CTkLabel(self, text="", font=Theme.FONT_CAPTION, text_color=Theme.DEBIT_RED)
        self.err.pack(pady=(6, 0))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=36, pady=16)
        ctk.CTkButton(btn_row, text="Cancel", fg_color="transparent", hover_color=Theme.BG_TERTIARY,
                      border_width=1, border_color=Theme.BORDER_COLOR, text_color=Theme.TEXT_PRIMARY,
                      command=self.destroy).pack(side="left", expand=True, fill="x", padx=(0,8))
        ctk.CTkButton(btn_row, text="Reset Password", fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER,
                      command=self._reset).pack(side="right", expand=True, fill="x")

    def _reset(self):
        pw = self.pw_entry.get(); pw2 = self.pw2_entry.get()
        if pw != pw2:
            self.err.configure(text="Passwords do not match."); return
        ok, msg = self.svc.reset_password(self.user_id, pw)
        if ok:
            self.audit.log(AuditAction.PASSWORD_RESET, f"Password reset for user ID {self.user_id}")
            self.on_success(); self.destroy()
        else:
            self.err.configure(text=msg)


# ── Main User Management Screen ─────────────────────────────────────────────

class UserManagementScreen(ctk.CTkFrame):
    """Owner-only admin screen for managing user accounts and viewing audit logs."""

    def __init__(self, parent, user_mgmt_service: UserManagementService, audit_service: AuditService):
        super().__init__(parent, fg_color="transparent")
        self.svc   = user_mgmt_service
        self.audit = audit_service

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Header ────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr, text="User Management",
            font=Theme.FONT_TITLE, text_color=Theme.TEXT_PRIMARY, anchor="w"
        ).grid(row=0, column=0, sticky="w")

        self.count_lbl = ctk.CTkLabel(
            hdr, text="",
            font=Theme.FONT_BODY, text_color=Theme.TEXT_SECONDARY
        )
        self.count_lbl.grid(row=0, column=1, sticky="e", padx=(0, 12))

        ctk.CTkButton(
            hdr, text="+ Add User",
            font=Theme.FONT_BODY_BOLD,
            fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER,
            corner_radius=Theme.CORNER_RADIUS,
            command=self._open_add_dialog
        ).grid(row=0, column=2, sticky="e")

        # ── Tab View ──────────────────────────────────────────────────────
        self.tabs = ctk.CTkTabview(
            self,
            fg_color=Theme.BG_SECONDARY,
            corner_radius=Theme.CORNER_RADIUS,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR,
            segmented_button_fg_color=Theme.BG_TERTIARY,
            segmented_button_selected_color=Theme.ACCENT,
            segmented_button_selected_hover_color=Theme.ACCENT_HOVER,
            segmented_button_unselected_color=Theme.BG_TERTIARY,
            segmented_button_unselected_hover_color=Theme.BORDER_COLOR,
            text_color=Theme.TEXT_PRIMARY,
        )
        self.tabs.grid(row=1, column=0, sticky="nsew")
        self.tabs.add("Users")
        self.tabs.add("Audit Log")

        # Users tab
        users_tab = self.tabs.tab("Users")
        users_tab.grid_columnconfigure(0, weight=1)
        users_tab.grid_rowconfigure(1, weight=1)
        self._build_users_tab(users_tab)

        # Audit tab
        audit_tab = self.tabs.tab("Audit Log")
        audit_tab.grid_columnconfigure(0, weight=1)
        audit_tab.grid_rowconfigure(0, weight=1)
        self._build_audit_tab(audit_tab)

        self.refresh()

    # ── Users Tab ────────────────────────────────────────────────────────────

    def _build_users_tab(self, parent):
        # Column header
        hdr = ctk.CTkFrame(parent, fg_color=Theme.BG_TERTIARY, corner_radius=0, height=36)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        cols = [("Username", 3), ("Role", 1), ("Status", 1), ("Last Login", 2), ("Actions", 3)]
        for i, (label, _) in enumerate(cols):
            hdr.grid_columnconfigure(i, weight=cols[i][1])
            ctk.CTkLabel(hdr, text=label.upper(), font=Theme.FONT_HEADER,
                         text_color=Theme.TEXT_PRIMARY, pady=8).grid(row=0, column=i, sticky="ew", padx=12)

        self.user_list = ctk.CTkScrollableFrame(parent, fg_color="transparent", corner_radius=0)
        self.user_list.grid(row=1, column=0, sticky="nsew")
        for i, (_, weight) in enumerate(cols):
            self.user_list.grid_columnconfigure(i, weight=weight)

    def _build_audit_tab(self, parent):
        self.audit_list = ctk.CTkScrollableFrame(parent, fg_color="transparent", corner_radius=0)
        self.audit_list.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.audit_list.grid_columnconfigure(0, weight=2)
        self.audit_list.grid_columnconfigure(1, weight=1)
        self.audit_list.grid_columnconfigure(2, weight=3)
        self.audit_list.grid_columnconfigure(3, weight=2)

    # ── Refresh ───────────────────────────────────────────────────────────────

    def refresh(self):
        self._refresh_users()
        self._refresh_audit()

    def _refresh_users(self):
        for w in self.user_list.winfo_children():
            w.destroy()

        users = self.svc.get_all_users()
        active_count = sum(1 for u in users if u.is_active)
        self.count_lbl.configure(text=f"{active_count} / {MAX_USERS} active users")

        current_user = SessionManager.get_current_user()

        for idx, user in enumerate(users):
            bg = Theme.BG_SECONDARY if idx % 2 == 0 else Theme.BG_PRIMARY
            is_self = current_user and user.id == current_user.id

            # Username cell
            name_cell = ctk.CTkFrame(self.user_list, fg_color=bg, corner_radius=0)
            name_cell.grid(row=idx, column=0, sticky="nsew", ipady=10)
            lbl_name = ctk.CTkLabel(
                name_cell,
                text=f"{user.username}  {'(you)' if is_self else ''}",
                font=Theme.FONT_BODY_BOLD if is_self else Theme.FONT_BODY,
                text_color=Theme.ACCENT if is_self else Theme.TEXT_PRIMARY,
                anchor="w"
            )
            lbl_name.pack(side="left", padx=12)

            # Role badge cell
            role_cell = ctk.CTkFrame(self.user_list, fg_color=bg, corner_radius=0)
            role_cell.grid(row=idx, column=1, sticky="nsew", ipady=10)
            role_color = _role_color(user.role)
            ctk.CTkLabel(
                role_cell,
                text=f" {user.display_role()} ",
                font=(Theme.FONT_FAMILY, 10, "bold"),
                text_color=role_color,
                fg_color=Theme.BG_TERTIARY,
                corner_radius=6
            ).pack(padx=8)

            # Status cell
            status_cell = ctk.CTkFrame(self.user_list, fg_color=bg, corner_radius=0)
            status_cell.grid(row=idx, column=2, sticky="nsew", ipady=10)
            status_text  = "Active" if user.is_active else "Disabled"
            status_color = Theme.CREDIT_GREEN if user.is_active else Theme.DEBIT_RED
            ctk.CTkLabel(status_cell, text=status_text, font=Theme.FONT_BODY,
                         text_color=status_color).pack()

            # Last Login cell
            ll_cell = ctk.CTkFrame(self.user_list, fg_color=bg, corner_radius=0)
            ll_cell.grid(row=idx, column=3, sticky="nsew", ipady=10)
            ll_text = user.last_login[:16] if user.last_login else "Never"
            ctk.CTkLabel(ll_cell, text=ll_text, font=Theme.FONT_CAPTION,
                         text_color=Theme.TEXT_SECONDARY).pack()

            # Actions cell
            action_cell = ctk.CTkFrame(self.user_list, fg_color=bg, corner_radius=0)
            action_cell.grid(row=idx, column=4, sticky="nsew", ipady=8)
            btn_box = ctk.CTkFrame(action_cell, fg_color="transparent")
            btn_box.pack(anchor="center")

            ctk.CTkButton(
                btn_box, text="Edit", width=52, height=24, font=Theme.FONT_CAPTION,
                fg_color="transparent", hover_color=Theme.BG_TERTIARY,
                border_width=1, border_color=Theme.BORDER_COLOR,
                text_color=Theme.TEXT_PRIMARY,
                command=lambda u=user: self._open_edit_dialog(u)
            ).pack(side="left", padx=2)

            ctk.CTkButton(
                btn_box, text="Pwd", width=44, height=24, font=Theme.FONT_CAPTION,
                fg_color="transparent", hover_color=Theme.BG_TERTIARY,
                border_width=1, border_color=Theme.BORDER_COLOR,
                text_color=Theme.TEXT_PRIMARY,
                command=lambda u=user: self._open_reset_pw(u)
            ).pack(side="left", padx=2)

            if not is_self:
                toggle_text  = "Enable" if not user.is_active else "Disable"
                toggle_color = Theme.CREDIT_GREEN if not user.is_active else Theme.WARNING_ORANGE
                ctk.CTkButton(
                    btn_box, text=toggle_text, width=58, height=24, font=Theme.FONT_CAPTION,
                    fg_color="transparent", hover_color=Theme.BG_TERTIARY,
                    border_width=1, border_color=toggle_color,
                    text_color=toggle_color,
                    command=lambda u=user: self._toggle_user(u)
                ).pack(side="left", padx=2)

                ctk.CTkButton(
                    btn_box, text="Delete", width=58, height=24, font=Theme.FONT_CAPTION,
                    fg_color="transparent", hover_color=Theme.DANGER_HOVER,
                    border_width=1, border_color=Theme.DEBIT_RED,
                    text_color=Theme.DEBIT_RED,
                    command=lambda u=user: self._confirm_delete(u)
                ).pack(side="left", padx=2)

    def _refresh_audit(self):
        for w in self.audit_list.winfo_children():
            w.destroy()

        logs = self.audit.get_recent_logs(200)

        # Header
        headers = [("User", 0), ("Action", 1), ("Details", 2), ("Timestamp", 3)]
        for col, (label, col_idx) in enumerate(headers):
            ctk.CTkLabel(
                self.audit_list,
                text=label.upper(),
                font=Theme.FONT_HEADER,
                text_color=Theme.TEXT_PRIMARY,
                fg_color=Theme.BG_TERTIARY,
                anchor="w", pady=6
            ).grid(row=0, column=col_idx, sticky="ew", padx=10)

        for i, entry in enumerate(logs):
            row_idx = i + 1
            bg = Theme.BG_SECONDARY if i % 2 == 0 else Theme.BG_PRIMARY

            for col_idx, text in enumerate([
                entry.get("username", "system"),
                entry.get("action", ""),
                (entry.get("details", "") or "")[:60],
                (entry.get("timestamp", "") or "")[:16]
            ]):
                cell = ctk.CTkFrame(self.audit_list, fg_color=bg, corner_radius=0)
                cell.grid(row=row_idx, column=col_idx, sticky="nsew", ipady=6)
                color = Theme.DEBIT_RED if "DELETE" in str(entry.get("action","")) else Theme.TEXT_PRIMARY
                ctk.CTkLabel(cell, text=text, font=Theme.FONT_CAPTION,
                             text_color=color if col_idx == 1 else Theme.TEXT_SECONDARY,
                             anchor="w").pack(side="left", padx=8)

        if not logs:
            ctk.CTkLabel(self.audit_list, text="No audit entries yet.",
                         font=Theme.FONT_BODY, text_color=Theme.TEXT_SECONDARY).grid(row=1, column=0, columnspan=4, pady=30)

    # ── Dialog launchers ─────────────────────────────────────────────────────

    def _open_add_dialog(self):
        UserFormDialog(self.winfo_toplevel(), self.svc, self.audit, on_success=self.refresh)

    def _open_edit_dialog(self, user):
        UserFormDialog(
            self.winfo_toplevel(), self.svc, self.audit, on_success=self.refresh,
            user_id=user.id, username=user.username, role=user.role
        )

    def _open_reset_pw(self, user):
        ResetPasswordDialog(
            self.winfo_toplevel(), self.svc, self.audit,
            user_id=user.id, username=user.username, on_success=self.refresh
        )

    def _toggle_user(self, user):
        curr = SessionManager.get_current_user()
        if user.is_active:
            ok, msg = self.svc.disable_user(user.id, curr.id)
            if ok:
                self.audit.log(AuditAction.USER_DISABLED, f"User '{user.username}' disabled")
        else:
            ok, msg = self.svc.enable_user(user.id)
            if ok:
                self.audit.log(AuditAction.USER_ENABLED, f"User '{user.username}' enabled")
        if ok:
            self.refresh()
        else:
            messagebox.showerror("Error", msg)

    def _confirm_delete(self, user):
        curr = SessionManager.get_current_user()
        if messagebox.askyesno(
            "Confirm Delete",
            f"Delete user '{user.username}'?\n\nThis cannot be undone.",
            icon="warning"
        ):
            ok, msg = self.svc.delete_user(user.id, curr.id)
            if ok:
                self.audit.log(AuditAction.USER_DELETED, f"User '{user.username}' deleted")
                self.refresh()
            else:
                messagebox.showerror("Cannot Delete", msg)
