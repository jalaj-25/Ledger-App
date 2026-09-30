"""
pdf_security_service.py
-----------------------
Enterprise-grade PDF security service for the Jalaj Ledger Management System.

Responsibilities:
  - Password hashing via PBKDF2-HMAC-SHA256 with random salt (never stores plaintext)
  - Password verification against stored hash + salt
  - Password strength validation (min 8 chars, upper, lower, digit, special)
  - PDF encryption via PyPDF2 (AES-128 owner + user password)
  - Atomic read/write of pdf security fields inside settings.json
  - XOR obfuscation of the raw password for at-rest storage
    (prevents casual plaintext exposure; not a cryptographic secret)

Design:
  - Zero coupling to any UI layer — pure service/logic module
  - All operations return structured results; never raises to caller silently
  - Encryption failures are returned as (False, reason) — app never crashes
"""

import os
import json
import hashlib
import secrets
import string
import tempfile
import shutil
from typing import Tuple, Optional

# --------------------------------------------------------------------------- #
#  Constants
# --------------------------------------------------------------------------- #
SETTINGS_FILE    = "settings.json"
PBKDF2_ALGO      = "sha256"
PBKDF2_ITERS     = 100_000   # NIST recommendation (>= 100k for SHA-256)
SALT_BYTES       = 16        # 128-bit random salt
SPECIAL_CHARS    = set(string.punctuation)


class PdfSecurityService:
    """
    Handles all PDF password-protection concerns for the ledger application.

    Usage pattern (in ExportService):
        svc = PdfSecurityService()
        if svc.is_security_enabled():
            ok, err = svc.encrypt_pdf(path, path)
    """

    # ------------------------------------------------------------------ #
    #  Password Hashing
    # ------------------------------------------------------------------ #

    @staticmethod
    def hash_password(password: str) -> Tuple[str, str]:
        """
        Hashes a plaintext password with a freshly-generated random salt.

        Returns:
            (salt_hex, hash_hex)  — both stored in settings.json
            Salt is 16 random bytes encoded as 32 hex chars.
            Hash is PBKDF2-HMAC-SHA256 output encoded as 64 hex chars.
        """
        salt_bytes = secrets.token_bytes(SALT_BYTES)
        hash_bytes = hashlib.pbkdf2_hmac(
            PBKDF2_ALGO,
            password.encode("utf-8"),
            salt_bytes,
            PBKDF2_ITERS
        )
        return salt_bytes.hex(), hash_bytes.hex()

    @staticmethod
    def verify_password(password: str, stored_hash: str, stored_salt: str) -> bool:
        """
        Verifies a candidate plaintext password against stored hash + salt.

        Uses a constant-time comparison (hmac.compare_digest equivalent via
        secrets.compare_digest) to prevent timing-based side-channel attacks.
        """
        try:
            salt_bytes = bytes.fromhex(stored_salt)
            candidate_hash = hashlib.pbkdf2_hmac(
                PBKDF2_ALGO,
                password.encode("utf-8"),
                salt_bytes,
                PBKDF2_ITERS
            ).hex()
            # Constant-time string comparison
            return secrets.compare_digest(candidate_hash, stored_hash)
        except Exception as e:
            print(f"[PdfSecurity] Password verification error: {e}")
            return False

    # ------------------------------------------------------------------ #
    #  Password Strength Validation
    # ------------------------------------------------------------------ #

    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, str]:
        """
        Validates a password against the application's complexity policy.

        Policy:
          - Minimum 8 characters
          - At least 1 uppercase letter
          - At least 1 lowercase letter
          - At least 1 digit
          - At least 1 special character (punctuation)

        Returns:
            (True, "")              on success
            (False, reason_string)  on failure
        """
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
        if not any(c in SPECIAL_CHARS for c in password):
            return False, "Password must contain at least one special character (e.g. @, #, !, $)."
        return True, ""

    @staticmethod
    def get_password_strength_score(password: str) -> int:
        """
        Returns a strength score 0-4 for UI strength meter display.
          0 = Very Weak
          1 = Weak
          2 = Fair
          3 = Strong
          4 = Very Strong
        """
        if not password:
            return 0
        score = 0
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in SPECIAL_CHARS for c in password)
        if has_upper and has_lower:
            score += 1
        if has_digit and has_special:
            score += 1
        return min(score, 4)

    # ------------------------------------------------------------------ #
    #  PDF Encryption
    # ------------------------------------------------------------------ #

    @staticmethod
    def encrypt_pdf(input_path: str, output_path: str, password: str) -> Tuple[bool, str]:
        """
        Encrypts a PDF file using AES-128 encryption (PyPDF2).

        Both owner and user passwords are set to the same value so the user
        must enter the password to open the file in any PDF viewer.

        Writes output atomically:
          - Encrypts to a temp file in the same directory
          - Only replaces the original if encryption fully succeeds

        Args:
            input_path:  Path to the source (unencrypted) PDF.
            output_path: Path for the encrypted PDF (can equal input_path).
            password:    Plaintext password string.

        Returns:
            (True, "")            on success
            (False, error_msg)    on any failure
        """
        try:
            # pyrefly: ignore [missing-import]
            import PyPDF2
        except ImportError:
            return False, "PyPDF2 library is not installed. Run: pip install pypdf2"

        if not os.path.isfile(input_path):
            return False, f"Source PDF not found: {input_path}"

        if not password:
            return False, "Encryption password is empty."

        # Use a temp file in the same directory for atomic replacement
        dir_name = os.path.dirname(os.path.abspath(output_path))
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".tmp.pdf", dir=dir_name)

        try:
            os.close(tmp_fd)  # Close fd — PyPDF2 will open by path

            with open(input_path, "rb") as src_file:
                reader = PyPDF2.PdfReader(src_file)
                writer = PyPDF2.PdfWriter()

                # Copy all pages
                for page in reader.pages:
                    writer.add_page(page)

                # Apply encryption (owner_pwd=password, user_pwd=password)
                writer.encrypt(
                    user_password=password,
                    owner_password=password,
                    use_128bit=True
                )

                with open(tmp_path, "wb") as dst_file:
                    writer.write(dst_file)

            # Verify the output is not empty
            if os.path.getsize(tmp_path) == 0:
                os.remove(tmp_path)
                return False, "Encryption produced an empty file — aborting."

            # Atomic replace (works cross-platform)
            shutil.move(tmp_path, output_path)
            return True, ""

        except Exception as e:
            # Clean up temp file on any error
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
            return False, f"Encryption failed: {e}"

    # ------------------------------------------------------------------ #
    #  Settings I/O
    # ------------------------------------------------------------------ #

    @staticmethod
    def _load_settings() -> dict:
        """Loads and returns the full settings.json dict, or empty dict on error."""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[PdfSecurity] Error reading settings: {e}")
        return {}

    @staticmethod
    def _save_settings(data: dict) -> None:
        """Writes the full settings dict back to settings.json."""
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"[PdfSecurity] Error writing settings: {e}")

    @classmethod
    def load_pdf_security_settings(cls) -> dict:
        """
        Returns the pdf-security block from settings.json.

        Keys returned:
            pdf_security_enabled (bool)
            password_hash        (str | "")
            salt                 (str | "")
        """
        data = cls._load_settings()
        return {
            "pdf_security_enabled": data.get("pdf_security_enabled", False),
            "password_hash": data.get("password_hash", ""),
            "salt": data.get("salt", ""),
        }

    @classmethod
    def save_pdf_security_settings(
        cls,
        enabled: bool,
        password_hash: str,
        salt: str,
        raw_password: str = ""
    ) -> None:
        """
        Persists pdf-security fields into settings.json without touching
        any other existing keys.

        Args:
            enabled:       Whether PDF encryption is active.
            password_hash: Hex-encoded PBKDF2 hash (for UI verification).
            salt:          Hex-encoded random salt used during hashing.
            raw_password:  The plaintext password (stored XOR-obfuscated as
                           'pdf_user_key' so the export service can use it
                           at PDF generation time without prompting the user).
        """
        data = cls._load_settings()
        data["pdf_security_enabled"] = enabled
        data["password_hash"] = password_hash
        data["salt"] = salt
        # Store XOR-obfuscated key for export-time encryption
        if raw_password and salt:
            data["pdf_user_key"] = cls.obfuscate_key(raw_password, salt)
        elif not raw_password and "pdf_user_key" in data:
            # Preserve existing key when called without a new password
            pass
        # Explicitly ensure the raw password is never stored under any clear key
        data.pop("pdf_password", None)
        cls._save_settings(data)

    @classmethod
    def is_security_enabled(cls) -> bool:
        """Returns True if PDF security is enabled AND a password is configured."""
        sec = cls.load_pdf_security_settings()
        return (
            sec.get("pdf_security_enabled", False)
            and bool(sec.get("password_hash"))
            and bool(sec.get("salt"))
        )

    @classmethod
    def get_active_password_hash_and_salt(cls) -> Tuple[Optional[str], Optional[str]]:
        """
        Returns (hash_hex, salt_hex) if security is enabled and configured,
        or (None, None) otherwise.
        """
        sec = cls.load_pdf_security_settings()
        if (
            sec.get("pdf_security_enabled", False)
            and sec.get("password_hash")
            and sec.get("salt")
        ):
            return sec["password_hash"], sec["salt"]
        return None, None

    @classmethod
    def set_enabled(cls, enabled: bool) -> None:
        """Toggles the pdf_security_enabled flag without changing hash/salt/key."""
        data = cls._load_settings()
        data["pdf_security_enabled"] = enabled
        cls._save_settings(data)

    # ------------------------------------------------------------------ #
    #  Key Obfuscation (XOR-based, local-disk protection)
    # ------------------------------------------------------------------ #

    @staticmethod
    def obfuscate_key(raw_password: str, salt_hex: str) -> str:
        """
        XOR-obfuscates the raw password using the stored salt as a keystream.
        Produces a hex-encoded string safe to store in settings.json.

        This is NOT cryptographic secrecy — it prevents casual plaintext
        exposure in the settings file while still allowing the export service
        to recover the raw password for PDF encryption at runtime.
        """
        try:
            pw_bytes   = raw_password.encode("utf-8")
            salt_bytes = bytes.fromhex(salt_hex)
            # Expand salt to cover full password length by repeating
            key_stream = (salt_bytes * (len(pw_bytes) // len(salt_bytes) + 1))[:len(pw_bytes)]
            xored = bytes(p ^ k for p, k in zip(pw_bytes, key_stream))
            return xored.hex()
        except Exception as e:
            print(f"[PdfSecurity] obfuscate_key error: {e}")
            return ""

    @staticmethod
    def deobfuscate_key(obfuscated_hex: str, salt_hex: str) -> str:
        """
        Reverses XOR obfuscation to recover the raw password string.
        Returns empty string on any decoding failure.
        """
        try:
            xored      = bytes.fromhex(obfuscated_hex)
            salt_bytes = bytes.fromhex(salt_hex)
            key_stream = (salt_bytes * (len(xored) // len(salt_bytes) + 1))[:len(xored)]
            pw_bytes   = bytes(x ^ k for x, k in zip(xored, key_stream))
            return pw_bytes.decode("utf-8")
        except Exception as e:
            print(f"[PdfSecurity] deobfuscate_key error: {e}")
            return ""
