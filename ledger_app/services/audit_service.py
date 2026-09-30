"""
audit_service.py
----------------
Thin service layer over AuditRepository.
Provides named action constants and convenience logging methods
with automatic user attribution from SessionManager.
"""

from typing import List, Dict, Any, Optional
from ledger_app.repositories.audit_repository import AuditRepository
from ledger_app.services.session_manager import SessionManager


class AuditAction:
    """Named constants for every auditable event."""
    LOGIN              = "LOGIN"
    LOGOUT             = "LOGOUT"
    SESSION_EXPIRED    = "SESSION_EXPIRED"
    CUSTOMER_ADDED     = "CUSTOMER_ADDED"
    CUSTOMER_EDITED    = "CUSTOMER_EDITED"
    CUSTOMER_DELETED   = "CUSTOMER_DELETED"
    TRANSACTION_ADDED  = "TRANSACTION_ADDED"
    TRANSACTION_DELETED = "TRANSACTION_DELETED"
    REPORT_GENERATED   = "REPORT_GENERATED"
    BACKUP_CREATED     = "BACKUP_CREATED"
    BACKUP_RESTORED    = "BACKUP_RESTORED"
    SETTINGS_MODIFIED  = "SETTINGS_MODIFIED"
    USER_CREATED       = "USER_CREATED"
    USER_UPDATED       = "USER_UPDATED"
    USER_DELETED       = "USER_DELETED"
    USER_DISABLED      = "USER_DISABLED"
    USER_ENABLED       = "USER_ENABLED"
    PASSWORD_CHANGED   = "PASSWORD_CHANGED"
    PASSWORD_RESET     = "PASSWORD_RESET"
    OTP_GENERATED      = "OTP_GENERATED"
    OTP_SENT           = "OTP_SENT"
    OTP_VERIFIED       = "OTP_VERIFIED"
    FAILED_ATTEMPTS    = "FAILED_ATTEMPTS"
    PIN_SET            = "PIN_SET"
    PIN_RESET          = "PIN_RESET"
    IMPORT_COMPLETED   = "IMPORT_COMPLETED"
    SYSTEM_INIT        = "SYSTEM_INIT"


class AuditService:
    """Convenience wrapper around AuditRepository with automatic session attribution."""

    def __init__(self, audit_repo: AuditRepository):
        self.repo = audit_repo

    def _current_user_info(self):
        """Returns (user_id, username) from the active session, or (None, 'system')."""
        user = SessionManager.get_current_user()
        if user:
            return user.id, user.username
        return None, "system"

    def log(self, action: str, details: str = "") -> None:
        """Logs an action attributed to the currently logged-in user."""
        user_id, username = self._current_user_info()
        self.repo.log(action, details, user_id=user_id, username=username)

    def log_as(
        self, action: str, details: str = "",
        user_id: Optional[int] = None, username: str = "system"
    ) -> None:
        """Logs an action with explicit user attribution (e.g. login events)."""
        self.repo.log(action, details, user_id=user_id, username=username)

    # ── Convenience Methods ───────────────────────────────────────────────────

    def log_login(self, user) -> None:
        self.log_as(AuditAction.LOGIN, f"User '{user.username}' logged in.", user.id, user.username)

    def log_logout(self, user) -> None:
        self.log_as(AuditAction.LOGOUT, f"User '{user.username}' logged out.", user.id, user.username)

    def log_session_expired(self, user) -> None:
        self.log_as(AuditAction.SESSION_EXPIRED, f"Session expired for '{user.username}'.", user.id, user.username)

    def log_customer_added(self, customer_name: str) -> None:
        self.log(AuditAction.CUSTOMER_ADDED, f"Customer added: {customer_name}")

    def log_customer_edited(self, customer_name: str) -> None:
        self.log(AuditAction.CUSTOMER_EDITED, f"Customer edited: {customer_name}")

    def log_customer_deleted(self, customer_name: str) -> None:
        self.log(AuditAction.CUSTOMER_DELETED, f"Customer deleted: {customer_name}")

    def log_transaction_added(self, details: str) -> None:
        self.log(AuditAction.TRANSACTION_ADDED, details)

    def log_report_generated(self, report_type: str) -> None:
        self.log(AuditAction.REPORT_GENERATED, f"Report generated: {report_type}")

    def log_backup_restored(self, backup_name: str) -> None:
        self.log(AuditAction.BACKUP_RESTORED, f"Backup restored: {backup_name}")

    def log_settings_modified(self, details: str = "") -> None:
        self.log(AuditAction.SETTINGS_MODIFIED, details)

    def log_import_completed(self, details: str) -> None:
        self.log(AuditAction.IMPORT_COMPLETED, details)

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_recent_logs(self, limit: int = 200) -> List[Dict[str, Any]]:
        return self.repo.get_recent(limit)

    def get_logs_for_user(self, user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        return self.repo.get_by_user(user_id, limit)
