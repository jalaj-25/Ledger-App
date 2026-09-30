"""
user_management_service.py
--------------------------
Owner-only business logic for managing user accounts:
  - Create / update / delete / disable users
  - Enforces 10-user maximum
  - Prevents Owner from deleting or disabling their own account
"""

from typing import List, Tuple, Optional
from ledger_app.models.user import User, ROLES, ROLE_OWNER, MAX_USERS
from ledger_app.repositories.user_repository import UserRepository
from ledger_app.services.auth_service import AuthService


class UserManagementService:

    def __init__(self, user_repo: UserRepository, auth_service: AuthService):
        self.repo = user_repo
        self.auth = auth_service

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_all_users(self) -> List[User]:
        return self.repo.find_all()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.repo.find_by_id(user_id)

    def get_user_count(self) -> int:
        return self.repo.get_user_count()

    # ── Create ────────────────────────────────────────────────────────────────

    def create_user(
        self, username: str, password: str, role: str
    ) -> Tuple[bool, str]:
        """
        Creates a new user account.
        Returns (True, "") on success or (False, error_msg) on failure.
        """
        username = username.strip()
        if not username:
            return False, "Username cannot be empty."
        if len(username) < 3:
            return False, "Username must be at least 3 characters."
        if not username.replace("_", "").replace(".", "").isalnum():
            return False, "Username may only contain letters, numbers, underscores, and dots."

        if role not in ROLES:
            return False, f"Invalid role. Must be one of: {', '.join(ROLES)}."

        # Enforce 10-user limit (count ALL users including inactive)
        all_users = self.repo.find_all()
        if len(all_users) >= MAX_USERS:
            return False, f"Maximum of {MAX_USERS} users reached. Delete or disable an existing user first."

        if self.repo.username_exists(username):
            return False, f"Username '{username}' is already taken."

        ok, msg = AuthService._validate_new_password(password)
        if not ok:
            return False, msg

        salt_hex, hash_hex = AuthService.hash_new_password(password)
        self.repo.create(username, hash_hex, salt_hex, role)
        return True, f"User '{username}' created successfully."

    # ── Update ────────────────────────────────────────────────────────────────

    def update_username(
        self, user_id: int, new_username: str, requesting_user_id: int
    ) -> Tuple[bool, str]:
        new_username = new_username.strip()
        if not new_username or len(new_username) < 3:
            return False, "Username must be at least 3 characters."
        if self.repo.username_exists(new_username, exclude_id=user_id):
            return False, f"Username '{new_username}' is already taken."
        self.repo.update_username(user_id, new_username)
        return True, "Username updated."

    def update_role(
        self, user_id: int, new_role: str, requesting_user_id: int
    ) -> Tuple[bool, str]:
        if new_role not in ROLES:
            return False, "Invalid role."
        if user_id == requesting_user_id:
            return False, "You cannot change your own role."
        # Ensure at least one owner remains
        if new_role != ROLE_OWNER:
            user = self.repo.find_by_id(user_id)
            if user and user.is_owner:
                all_users = self.repo.find_all()
                owner_count = sum(1 for u in all_users if u.is_owner)
                if owner_count <= 1:
                    return False, "Cannot demote the only Owner account."
        self.repo.update_role(user_id, new_role)
        return True, "Role updated."

    def reset_password(
        self, user_id: int, new_password: str
    ) -> Tuple[bool, str]:
        return self.auth.admin_reset_password(user_id, new_password)

    def reset_pin(self, user_id: int) -> Tuple[bool, str]:
        ok = self.auth.clear_pin(user_id)
        return (True, "PIN cleared.") if ok else (False, "Failed to clear PIN.")

    # ── Enable / Disable ──────────────────────────────────────────────────────

    def disable_user(
        self, user_id: int, requesting_user_id: int
    ) -> Tuple[bool, str]:
        if user_id == requesting_user_id:
            return False, "You cannot disable your own account."

        user = self.repo.find_by_id(user_id)
        if user and user.is_owner:
            all_users = self.repo.find_all()
            active_owners = [u for u in all_users if u.is_owner and u.is_active]
            if len(active_owners) <= 1:
                return False, "Cannot disable the only active Owner account."

        self.repo.set_active(user_id, False)
        return True, "User account disabled."

    def enable_user(self, user_id: int) -> Tuple[bool, str]:
        self.repo.set_active(user_id, True)
        return True, "User account enabled."

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete_user(
        self, user_id: int, requesting_user_id: int
    ) -> Tuple[bool, str]:
        if user_id == requesting_user_id:
            return False, "You cannot delete your own account."

        user = self.repo.find_by_id(user_id)
        if user and user.is_owner:
            all_users = self.repo.find_all()
            owner_count = sum(1 for u in all_users if u.is_owner)
            if owner_count <= 1:
                return False, "Cannot delete the only Owner account."

        self.repo.delete(user_id)
        return True, "User deleted."
