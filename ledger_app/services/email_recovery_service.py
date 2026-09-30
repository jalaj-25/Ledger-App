import traceback
from typing import Optional
from ledger_app.services.email_service import EmailService

class EmailRecoveryService:
    """Service to format and dispatch password recovery OTPs via email."""

    @staticmethod
    def send_otp_email(recipient_email: str, otp: str, email_service: EmailService) -> bool:
        """
        Sends the 6-digit OTP code to the target recovery email address.
        
        Returns:
            True if sent successfully, False otherwise.
        """
        subject = "Jalaj Ledger - Account Password Recovery OTP"
        body = (
            "Hello,\n\n"
            "You requested a password recovery code for your Jalaj Ledger Management System account.\n\n"
            f"Your 6-Digit OTP is: {otp}\n\n"
            "This code is valid for 10 minutes and can only be used once.\n\n"
            "If you did not initiate this request, please contact the system administrator immediately and secure your account.\n\n"
            "Regards,\n"
            "Enterprise Security System"
        )
        
        try:
            print(f"[EmailRecoveryService] Sending recovery OTP to {recipient_email}...")
            success = email_service.send_email_report(subject, body, recipient_override=recipient_email)
            if success:
                print("[EmailRecoveryService] OTP email sent successfully.")
                return True
            else:
                print("[EmailRecoveryService] Failed to send OTP email via EmailService.")
                return False
        except Exception as e:
            print(f"[EmailRecoveryService] Error dispatching OTP email: {e}")
            traceback.print_exc()
            return False
