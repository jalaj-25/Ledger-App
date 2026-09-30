"""
auth_service.py
---------------
Handles all authentication operations:
  - Password login with PBKDF2-HMAC-SHA256 (same algorithm as PdfSecurityService)
  - PIN verification and setup
  - Password change / admin reset
"""

import hashlib
import secrets
from typing import Tuple, Optional

from ledger_app.models.user import User
from ledger_app.repositories.user_repository import UserRepository

# PBKDF2 parameters — must match PdfSecurityService for existing hash compatibility
_ALGO       = "sha256"
_ITERATIONS = 100_000
_SALT_BYTES = 16

MIN_PASSWORD_LENGTH = 6
MIN_PIN_LENGTH      = 4
MAX_PIN_LENGTH      = 6


def _hash_secret(secret: str, salt_hex: Optional[str] = None) -> Tuple[str, str]:
    """Hashes a password or PIN using PBKDF2-HMAC-SHA256.

    Returns:
        (salt_hex, hash_hex)
    """
    if salt_hex:
        salt = bytes.fromhex(salt_hex)
    else:
        salt = secrets.token_bytes(_SALT_BYTES)

    digest = hashlib.pbkdf2_hmac(_ALGO, secret.encode("utf-8"), salt, _ITERATIONS)
    return salt.hex(), digest.hex()


def _verify_secret(candidate: str, stored_hash: str, stored_salt: str) -> bool:
    """Constant-time comparison of candidate against stored PBKDF2 hash."""
    try:
        salt   = bytes.fromhex(stored_salt)
        digest = hashlib.pbkdf2_hmac(
            _ALGO, candidate.encode("utf-8"), salt, _ITERATIONS
        ).hex()
        return secrets.compare_digest(digest, stored_hash)
    except Exception as e:
        print(f"[AuthService] Verification error: {e}")
        return False


class AuthService:
    """Core authentication service. Stateless — session tracking is in SessionManager."""

    def __init__(self, user_repo: UserRepository):
        self.repo = user_repo

    # ── Login ─────────────────────────────────────────────────────────────────

    def login(self, username: str, password: str) -> Tuple[Optional[User], str]:
        """
        Validates credentials and returns (User, "") on success
        or (None, error_message) on failure.
        """
        username = username.strip()
        if not username or not password:
            return None, "Username and password are required."

        creds = self.repo.get_credentials(username)
        if creds is None:
            return None, "Invalid username or password."

        if not creds["is_active"]:
            return None, "This account has been disabled. Contact the Owner."

        if not _verify_secret(password, creds["password_hash"], creds["salt"]):
            return None, "Invalid username or password."

        # Update last_login timestamp
        self.repo.update_last_login(creds["id"])

        user = self.repo.find_by_id(creds["id"])
        return user, ""

    # ── PIN ───────────────────────────────────────────────────────────────────

    def verify_pin(self, user_id: int, pin: str) -> bool:
        """Returns True if the PIN matches the stored hash."""
        pin = pin.strip()
        if not pin:
            return False
        pin_creds = self.repo.get_pin_credentials(user_id)
        if not pin_creds:
            return False
        return _verify_secret(pin, pin_creds["pin_hash"], pin_creds["pin_salt"])

    def set_pin(self, user_id: int, pin: str) -> Tuple[bool, str]:
        """Hashes and stores a PIN for the given user."""
        pin = pin.strip()
        if not pin.isdigit():
            return False, "PIN must contain digits only."
        if not (MIN_PIN_LENGTH <= len(pin) <= MAX_PIN_LENGTH):
            return False, f"PIN must be {MIN_PIN_LENGTH}–{MAX_PIN_LENGTH} digits."

        salt_hex, hash_hex = _hash_secret(pin)
        ok = self.repo.update_pin(user_id, hash_hex, salt_hex)
        return ok, "" if ok else "Failed to save PIN."

    def clear_pin(self, user_id: int) -> bool:
        """Removes the PIN from the user account."""
        return self.repo.update_pin(user_id, None, None)

    def has_pin(self, user_id: int) -> bool:
        """Returns True if the user has a PIN configured."""
        return self.repo.get_pin_credentials(user_id) is not None

    # ── Password Management ───────────────────────────────────────────────────

    def change_password(
        self, user_id: int, old_password: str, new_password: str
    ) -> Tuple[bool, str]:
        """Allows a user to change their own password after verifying the old one."""
        creds = self.repo.get_credentials_by_id(user_id)
        if not creds:
            return False, "User not found."

        if not _verify_secret(old_password, creds["password_hash"], creds["salt"]):
            return False, "Current password is incorrect."

        ok, msg = self._validate_new_password(new_password)
        if not ok:
            return False, msg

        salt_hex, hash_hex = _hash_secret(new_password)
        self.repo.update_password(user_id, hash_hex, salt_hex)
        return True, "Password changed successfully."

    def admin_reset_password(
        self, user_id: int, new_password: str
    ) -> Tuple[bool, str]:
        """Owner-only: reset any user's password without knowing the old one."""
        ok, msg = self._validate_new_password(new_password)
        if not ok:
            return False, msg

        salt_hex, hash_hex = _hash_secret(new_password)
        self.repo.update_password(user_id, hash_hex, salt_hex)
        self.repo.set_must_change(user_id, False)
        return True, "Password reset successfully."

    @staticmethod
    def _validate_new_password(password: str) -> Tuple[bool, str]:
        if not password:
            return False, "Password cannot be empty."
        if len(password) < 8:
            return False, "Password must be at least 8 characters long."
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter (A-Z)."
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter (a-z)."
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number (0-9)."
        import string
        special_chars = set(string.punctuation)
        if not any(c in special_chars for c in password):
            return False, "Password must contain at least one special character (e.g. @, #, !, $)."
        return True, ""

    def must_change_password(self, user_id: int) -> bool:
        """Checks if a user is flagged as requiring a password change."""
        user = self.repo.find_by_id(user_id)
        return user.must_change if user else False

    # ── Hash helper (for user creation) ──────────────────────────────────────

    @staticmethod
    def hash_new_password(password: str) -> Tuple[str, str]:
        """Returns (salt_hex, hash_hex) for a new password."""
        return _hash_secret(password)
