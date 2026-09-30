import os
import json
import secrets
import hashlib

SETTINGS_FILE = "settings.json"

def preprocess_settings(settings_path: str = SETTINGS_FILE) -> None:
    """
    Scans settings.json for plaintext configurations:
      - 'sender_password': SMTP password
      - 'owner_password': Default owner login password
      - 'pdf_password': PDF security password
    
    If any are present, automatically hashes/obfuscates them, generates
    their salts, updates settings.json atomically, and pops the plaintext fields.
    """
    if not os.path.exists(settings_path):
        return

    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[Settings Preprocessor] Warning: Failed to read settings file: {e}")
        return

    if not isinstance(data, dict):
        return

    modified = False

    # 1. Process plaintext SMTP password
    if "sender_password" in data:
        sender_pw = data.pop("sender_password")
        if sender_pw:
            # Auto-generate 128-bit random salt
            salt_hex = secrets.token_bytes(16).hex()
            # Obfuscate using repeating XOR key stream from salt
            from ledger_app.services.pdf_security_service import PdfSecurityService
            obf_pw = PdfSecurityService.obfuscate_key(sender_pw, salt_hex)
            
            data["sender_password_obfuscated"] = obf_pw
            data["sender_password_salt"] = salt_hex
            modified = True
            print("[Settings Preprocessor] Automatically obfuscated SMTP password.")
        else:
            data["sender_password_obfuscated"] = ""
            data["sender_password_salt"] = ""
            modified = True

    # 2. Process plaintext owner password (used for initial DB seeding)
    if "owner_password" in data:
        owner_pw = data.pop("owner_password")
        if owner_pw:
            # Auto-generate 128-bit random salt
            salt_bytes = secrets.token_bytes(16)
            salt_hex = salt_bytes.hex()
            # Hash via PBKDF2-HMAC-SHA256
            hash_bytes = hashlib.pbkdf2_hmac(
                "sha256",
                owner_pw.encode("utf-8"),
                salt_bytes,
                100_000
            )
            data["password_hash"] = hash_bytes.hex()
            data["salt"] = salt_hex
            modified = True
            print("[Settings Preprocessor] Automatically generated salt and hash for owner_password.")
        else:
            data["password_hash"] = ""
            data["salt"] = ""
            modified = True

    # 3. Process plaintext PDF password
    if "pdf_password" in data:
        pdf_pw = data.pop("pdf_password")
        if pdf_pw:
            from ledger_app.services.pdf_security_service import PdfSecurityService
            salt_hex, hash_hex = PdfSecurityService.hash_password(pdf_pw)
            data["password_hash"] = hash_hex
            data["salt"] = salt_hex
            data["pdf_user_key"] = PdfSecurityService.obfuscate_key(pdf_pw, salt_hex)
            data["pdf_security_enabled"] = True
            modified = True
            print("[Settings Preprocessor] Automatically generated salt, hash, and key for pdf_password.")
        else:
            data["password_hash"] = ""
            data["salt"] = ""
            data["pdf_user_key"] = ""
            data["pdf_security_enabled"] = False
            modified = True

    if modified:
        try:
            # Write atomically to settings.json
            temp_path = settings_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            os.replace(temp_path, settings_path)
            print("[Settings Preprocessor] settings.json updated and secured.")
        except Exception as e:
            print(f"[Settings Preprocessor] Error: Failed to write updated settings: {e}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
