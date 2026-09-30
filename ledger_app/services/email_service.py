import os
import json
import smtplib
import traceback
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Tuple, Optional

# Hardcoded Email credentials (optional).
# If left as defaults, the application will read from the Settings screen / settings.json.
SENDER_EMAIL = "jalajsinghal25@gmail.com"
SENDER_PASSWORD = "icuqgjxvpmkmylmn"
RECIPIENT_EMAIL = "jalajsinghal@gmail.com"

class EmailService:
    """
    Instrumented Email Service that logs every execution step and provides complete tracebacks.
    """
    def __init__(self, config_path: str = "settings.json"):
        self.config_path = config_path
        print(f"[Email DEBUG] Service initialized. Config path: {os.path.abspath(config_path)}")

    def _load_config(self) -> Tuple[Optional[str], Optional[str], Optional[str], str, int]:
        """Loads SMTP configurations from hardcoded variables or settings.json."""
        sender_email = SENDER_EMAIL if SENDER_EMAIL != "jalajsinghal25@gmail.com" else None
        sender_password = SENDER_PASSWORD if SENDER_PASSWORD != "icuqgjxvpmkmylmn" else None
        recipient_email = RECIPIENT_EMAIL if RECIPIENT_EMAIL != "jalajsinghal@gmail.com" else None
        smtp_server = "smtp.gmail.com"
        smtp_port = 587

        print(f"[Email DEBUG] Evaluating hardcoded configurations:")
        print(f"  Hardcoded Sender: {sender_email}")
        print(f"  Hardcoded Password: {'[MASKED]' if sender_password else 'None'}")
        print(f"  Hardcoded Recipient: {recipient_email}")

        # Fallback to settings.json if hardcoded values are empty or defaults
        if not sender_email or not sender_password or not recipient_email:
            print(f"[Email DEBUG] Hardcoded values missing. Loading settings from settings.json...")
            if os.path.exists(self.config_path):
                try:
                    with open(self.config_path, "r") as f:
                        data = json.load(f)
                        if not sender_email:
                            sender_email = data.get("sender_email")
                            print(f"  Loaded Sender from JSON: {sender_email}")
                        
                        if not sender_password:
                            # Try secure obfuscated app password first
                            obf_pw = data.get("sender_password_obfuscated")
                            salt = data.get("sender_password_salt")
                            if obf_pw and salt:
                                from ledger_app.services.pdf_security_service import PdfSecurityService
                                sender_password = PdfSecurityService.deobfuscate_key(obf_pw, salt)
                                print("  Loaded secure obfuscated password from JSON.")
                            else:
                                sender_password = data.get("sender_password")
                                print(f"  Loaded Password from JSON: {'[MASKED]' if sender_password else 'None'}")
                                
                        if not recipient_email:
                            recipient_email = data.get("recipient_email")
                            print(f"  Loaded Recipient from JSON: {recipient_email}")
                        
                        smtp_server = data.get("smtp_server", "smtp.gmail.com")
                        smtp_port = int(data.get("smtp_port", 587))
                except Exception as e:
                    print(f"[Email DEBUG] Failed to load JSON configuration: {e}")
            else:
                print(f"[Email DEBUG] settings.json not found.")

        print(f"[Email DEBUG] Active configurations:")
        print(f"  Active Sender: {sender_email}")
        print(f"  Active Password: {'[MASKED]' if sender_password else 'None'}")
        print(f"  Active Recipient: {recipient_email}")
        print(f"  SMTP Server: {smtp_server}:{smtp_port}")

        return sender_email, sender_password, recipient_email, smtp_server, smtp_port

    def send_email_report(self, subject: str, body: str, attachment_path: Optional[str] = None, recipient_override: Optional[str] = None) -> bool:
        """
        Sends an email with an optional attachment, logging details of every phase.
        """
        print("[Email DEBUG] Beginning send_email_report flow...")
        sender_email, sender_password, recipient_email, smtp_server, smtp_port = self._load_config()
        
        if recipient_override:
            recipient_email = recipient_override
            print(f"[Email DEBUG] Recipient overridden to: {recipient_email}")

        if not sender_email or not sender_password or not recipient_email:
            print("[Email DEBUG] ERROR: One or more configuration parameters are missing. Aborting send.")
            return False

        # Phase 1: Build Message
        print("[Email DEBUG] Phase 1: Compiling message structure...")
        try:
            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = recipient_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))
            print(f"  Subject: '{subject}'")
        except Exception as e:
            print(f"[Email DEBUG] Phase 1 Error (Message Compilation): {e}")
            traceback.print_exc()
            return False

        # Phase 2: Attach File
        if attachment_path:
            abs_path = os.path.abspath(attachment_path)
            print(f"[Email DEBUG] Phase 2: Loading attachment from: {abs_path}")
            if os.path.exists(abs_path):
                try:
                    filename = os.path.basename(abs_path)
                    with open(abs_path, "rb") as attachment:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename= {filename}",
                        )
                        msg.attach(part)
                    print("  Attachment loaded and attached successfully.")
                except Exception as e:
                    print(f"[Email DEBUG] Phase 2 Error (Attachment Handling): {e}")
                    traceback.print_exc()
                    return False
            else:
                print(f"[Email DEBUG] WARNING: Attachment path does not exist. Sending email text only.")

        # Phase 3: Establish SMTP Connection and Send
        print(f"[Email DEBUG] Phase 3: Commencing SMTP connection to {smtp_server}:{smtp_port}...")
        server = None
        try:
            if smtp_port == 465:
                print("  Using SSL connection (Port 465)...")
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=15)
            else:
                print(f"  Using standard SMTP connection with STARTTLS (Port {smtp_port})...")
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
                print("  Sending STARTTLS command...")
                server.starttls()

            print("  SMTP connection established. Proceeding to authentication...")
            
            # Verify credentials reach the login call
            if sender_email and sender_password:
                print(f"  Attempting login for: {sender_email} (Password Length: {len(sender_password)})")
            
            server.login(sender_email, sender_password)
            print("  Authentication successful.")

            print("  Sending email payload...")
            server.sendmail(sender_email, recipient_email, msg.as_string())
            print("  Payload transmitted successfully.")
            return True

        except smtplib.SMTPAuthenticationError as auth_err:
            print(f"\n[Email DEBUG] AUTHENTICATION ERROR: Login failed.")
            print(f"  Details: {auth_err}")
            print("  Likely Root Cause: Either the credentials are typed wrong, or Gmail requires an App Password.")
            print("  Resolution: Enable 2FA on Gmail, generate a 16-character App Password, and put it in SENDER_PASSWORD.")
            return False

        except Exception as smtp_err:
            print(f"\n[Email DEBUG] Phase 3 Error (SMTP Connection/Dispatch): {smtp_err}")
            traceback.print_exc()
            return False

        finally:
            if server:
                try:
                    print("[Email DEBUG] Terminating SMTP connection...")
                    server.quit()
                    print("  SMTP connection closed cleanly.")
                except Exception:
                    pass
