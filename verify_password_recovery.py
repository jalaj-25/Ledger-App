import os
import sys
import datetime

# Add directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from ledger_app.database.db_connection import DatabaseManager
from ledger_app.repositories.user_repository import UserRepository
from ledger_app.services.auth_service import AuthService
from ledger_app.services.otp_service import OtpService

def run_recovery_tests():
    db_file = "test_recovery.db"
    if os.path.exists(db_file):
        os.remove(db_file)
        print("Cleared previous test DB.")

    db = DatabaseManager(db_path=db_file)
    repo = UserRepository(db)
    auth = AuthService(repo)

    # 1. Create a mock owner user
    print("Creating test owner...")
    pw_hash, salt = AuthService.hash_new_password("InitialPassword123!")
    user_id = repo.create("owner_test", pw_hash, salt, "owner")
    repo.update_recovery_email(user_id, "owner@example.com")
    
    # Verify retrieval
    info = repo.get_recovery_info("owner_test")
    assert info is not None
    assert info["recovery_email"] == "owner@example.com"
    print(f"Test owner created. Recovery Info: {info}")

    # 2. Test OTP Generation
    print("\nTesting OTP Generation...")
    otp = OtpService.generate_otp("owner_test")
    assert len(otp) == 6
    assert otp.isdigit()
    print(f"Generated 6-digit OTP: {otp}")

    # 3. Test OTP Verification (Success)
    print("\nTesting OTP Verification (Success)...")
    success, msg = OtpService.verify_otp("owner_test", otp, repo)
    assert success is True
    print(f"OTP verified successfully: {msg}")

    # 4. Test OTP Single-Use (Should fail on second attempt)
    print("\nTesting OTP Single-Use...")
    success, msg = OtpService.verify_otp("owner_test", otp, repo)
    assert success is False
    print(f"Verify failed as expected on second use: {msg}")

    # 5. Test OTP Expiry
    print("\nTesting OTP Expiry...")
    otp_exp = OtpService.generate_otp("owner_test")
    # Manually backdate expiry to test expiration
    OtpService._active_otps["owner_test"]["expiry"] = datetime.datetime.now() - datetime.timedelta(minutes=1)
    success, msg = OtpService.verify_otp("owner_test", otp_exp, repo)
    assert success is False
    assert "expired" in msg.lower()
    print(f"Expired OTP failed as expected: {msg}")

    # 6. Test Failed Attempts Lockout (Max 5 attempts)
    print("\nTesting Lockout after 5 failed attempts...")
    repo.reset_otp_attempts("owner_test")
    for i in range(1, 6):
        # We generate a new OTP so we bypass the "no active OTP found" code if desired, 
        # or we just try incorrect OTPs
        success, msg = OtpService.verify_otp("owner_test", "000000", repo)
        print(f"Attempt {i}: Success={success}, Message={msg}")
        
    # 6th attempt should block immediately due to active lockout
    is_locked, lock_msg = OtpService.is_locked_out("owner_test", repo)
    assert is_locked is True
    print(f"Account is locked out: {lock_msg}")

    # Clean up test DB
    if os.path.exists(db_file):
        os.remove(db_file)
        print("Cleaned up test DB.")

    print("\n*** ALL PASSWORD RECOVERY TESTS PASSED SUCCESSFULLY! ***")

if __name__ == "__main__":
    run_recovery_tests()
