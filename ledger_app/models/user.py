from dataclasses import dataclass, field
from typing import Optional, FrozenSet

# ── Role Constants ────────────────────────────────────────────────────────────

ROLE_OWNER = "owner"
ROLE_STAFF = "staff"
ROLES = [ROLE_OWNER, ROLE_STAFF]

# ── Permission Keys ───────────────────────────────────────────────────────────

class Permission:
    VIEW_DASHBOARD       = "view_dashboard"
    ADD_CUSTOMER         = "add_customer"
    EDIT_CUSTOMER        = "edit_customer"
    DELETE_CUSTOMER      = "delete_customer"
    VIEW_LEDGER          = "view_ledger"
    ADD_TRANSACTION      = "add_transaction"
    DELETE_TRANSACTION   = "delete_transaction"
    VIEW_REPORTS         = "view_reports"
    GENERATE_REPORTS     = "generate_reports"
    IMPORT_DATA          = "import_data"
    VIEW_SETTINGS        = "view_settings"
    EDIT_SETTINGS        = "edit_settings"
    USER_MANAGEMENT      = "user_management"
    BACKUP_RESTORE       = "backup_restore"
    VIEW_AUDIT_LOGS      = "view_audit_logs"


# Permission sets per role
OWNER_PERMISSIONS: FrozenSet[str] = frozenset([
    Permission.VIEW_DASHBOARD,
    Permission.ADD_CUSTOMER,
    Permission.EDIT_CUSTOMER,
    Permission.DELETE_CUSTOMER,
    Permission.VIEW_LEDGER,
    Permission.ADD_TRANSACTION,
    Permission.DELETE_TRANSACTION,
    Permission.VIEW_REPORTS,
    Permission.GENERATE_REPORTS,
    Permission.IMPORT_DATA,
    Permission.VIEW_SETTINGS,
    Permission.EDIT_SETTINGS,
    Permission.USER_MANAGEMENT,
    Permission.BACKUP_RESTORE,
    Permission.VIEW_AUDIT_LOGS,
])

STAFF_PERMISSIONS: FrozenSet[str] = frozenset([
    Permission.VIEW_DASHBOARD,
    Permission.ADD_CUSTOMER,
    Permission.EDIT_CUSTOMER,
    Permission.VIEW_LEDGER,
    Permission.ADD_TRANSACTION,
    Permission.VIEW_REPORTS,
    Permission.GENERATE_REPORTS,
])

ROLE_PERMISSIONS = {
    ROLE_OWNER: OWNER_PERMISSIONS,
    ROLE_STAFF: STAFF_PERMISSIONS,
}

MAX_USERS = 10


@dataclass
class User:
    """Domain model for an application user. Never carries raw password or hash fields."""
    id:             Optional[int]
    username:       str
    role:           str
    is_active:      bool
    created_at:     Optional[str] = None
    last_login:     Optional[str] = None
    must_change:    bool = False
    recovery_email: Optional[str] = None

    @property
    def is_owner(self) -> bool:
        return self.role == ROLE_OWNER

    @property
    def is_staff(self) -> bool:
        return self.role == ROLE_STAFF

    def has_permission(self, permission: str) -> bool:
        """Returns True if this user's role grants the requested permission."""
        perms = ROLE_PERMISSIONS.get(self.role, frozenset())
        return permission in perms

    def display_role(self) -> str:
        return "Owner" if self.is_owner else "Staff"

    @classmethod
    def from_row(cls, row) -> "User":
        d = dict(row)
        return cls(
            id=d.get("id"),
            username=d.get("username", ""),
            role=d.get("role", ROLE_STAFF),
            is_active=bool(d.get("is_active", 1)),
            created_at=d.get("created_at"),
            last_login=d.get("last_login"),
            must_change=bool(d.get("must_change", 0)),
            recovery_email=d.get("recovery_email"),
        )
