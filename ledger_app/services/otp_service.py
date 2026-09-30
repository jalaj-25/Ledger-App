import secrets
import datetime
from typing import Tuple, Dict, Optional
from ledger_app.repositories.user_repository import UserRepository

LOCKOUT_DURATION_MINUTES = 15
OTP_EXPIRY_MINUTES = 10
MAX_FAILED_ATTEMPTS = 5

class OtpService:
    """
    In-memory storage and validation of One-Time Passwords (OTP).
    Persists attempt metrics in the database user repository.
    """
    # In-memory dictionary: {username_lowercase: {"otp": code, "expiry": datetime}}
    _active_otps: Dict[str, dict] = {}

    @classmethod
    def generate_otp(cls, username: str) -> str:
        """Generates a secure 6-digit numeric OTP and stores it in-memory."""
        code = "".join(secrets.choice("0123456789") for _ in range(6))
        expiry = datetime.datetime.now() + datetime.timedelta(minutes=OTP_EXPIRY_MINUTES)
        cls._active_otps[username.lower()] = {
            "otp": code,
            "expiry": expiry
        }
        return code

    @classmethod
    def verify_otp(cls, username: str, code_candidate: str, user_repo: UserRepository) -> Tuple[bool, str]:
        """
        Verifies the candidate OTP against the stored code for the user.
        Decrements attempts/locks user on failure. Resets on success.
        
        Returns:
            (success: bool, message: str)
        """
        username_key = username.lower()
        
        # 1. Check lockout status first
        is_locked, msg = cls.is_locked_out(username, user_repo)
        if is_locked:
            return False, msg

        # 2. Retrieve recovery info to track attempts
        info = user_repo.get_recovery_info(username)
        if not info:
            return False, "User not found."

        # 3. Check if OTP exists in memory
        if username_key not in cls._active_otps:
            # Increment failed attempts in database
            attempts = user_repo.increment_otp_attempts(username)
            if attempts >= MAX_FAILED_ATTEMPTS:
                # Lockout is triggered. Set the timestamp of the request to now (since lockout is relative to this timestamp)
                user_repo.set_last_recovery_request(username, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                return False, f"Too many failed attempts. This account has been locked for {LOCKOUT_DURATION_MINUTES} minutes."
            return False, f"Invalid OTP. {MAX_FAILED_ATTEMPTS - attempts} attempts remaining."

        otp_data = cls._active_otps[username_key]

        # 4. Check OTP Expiry
        if datetime.datetime.now() > otp_data["expiry"]:
            cls._active_otps.pop(username_key, None)
            return False, "OTP has expired. Please request a new OTP."

        # 5. Compare candidate code
        if otp_data["otp"] != code_candidate:
            # Increment attempts
            attempts = user_repo.increment_otp_attempts(username)
            if attempts >= MAX_FAILED_ATTEMPTS:
                user_repo.set_last_recovery_request(username, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                return False, f"Too many failed attempts. This account has been locked for {LOCKOUT_DURATION_MINUTES} minutes."
            return False, f"Invalid OTP. {MAX_FAILED_ATTEMPTS - attempts} attempts remaining."

        # 6. Success: Clear OTP and reset attempts
        cls._active_otps.pop(username_key, None)
        user_repo.reset_otp_attempts(username)
        return True, "OTP verified successfully."

    @classmethod
    def is_locked_out(cls, username: str, user_repo: UserRepository) -> Tuple[bool, str]:
        """
        Checks if the username is currently locked out of recovery due to excessive attempts.
        
        Returns:
            (is_locked: bool, status_message: str)
        """
        info = user_repo.get_recovery_info(username)
        if not info:
            return False, ""

        attempts = info.get("otp_attempts", 0)
        if attempts < MAX_FAILED_ATTEMPTS:
            return False, ""

        # Check lockout time
        last_req_str = info.get("last_recovery_request")
        if not last_req_str:
            return False, ""

        try:
            last_req = datetime.datetime.strptime(last_req_str, "%Y-%m-%d %H:%M:%S")
            elapsed = datetime.datetime.now() - last_req
            remaining_seconds = (LOCKOUT_DURATION_MINUTES * 60) - elapsed.total_seconds()
            
            if remaining_seconds > 0:
                remaining_minutes = int(remaining_seconds // 60) + 1
                return True, f"This account is locked out of recovery. Please try again in {remaining_minutes} minutes."
            else:
                # Lockout expired, reset attempts
                user_repo.reset_otp_attempts(username)
                return False, ""
        except Exception:
            return False, ""

    @classmethod
    def clear_otp(cls, username: str):
        """Removes the active OTP code from memory."""
        cls._active_otps.pop(username.lower(), None)
