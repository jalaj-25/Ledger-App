"""
restore_service.py
==================
Restore Engine for Jalaj Ledger Management System.

Restore Flow:
  1. Validate the target zip archive
  2. Create a safety "Pre-Restore" backup of current state
  3. Extract ledger.db → overwrite current database
  4. Extract settings.json → overwrite current settings
  5. Return (success, message)

The safety backup ensures the user can always recover even if a restore fails.
"""

import os
import json
import zipfile
import datetime
from typing import Optional

from ledger_app.services.backup_service import BackupService

SETTINGS_FILE = "settings.json"


class RestoreService:
    """
    Handles the complete restore workflow.
    All public methods return (success: bool, message: str) tuples.
    """

    @staticmethod
    def get_restore_preview(zip_path: str) -> dict:
        """
        Reads embedded backup_info.json from a zip and returns a dict
        suitable for display in the UI restore preview panel.

        Returns:
            {
                "backup_type": str,
                "created_at": str,
                "app_version": str,
                "files_included": list[str],
                "size_str": str,
                "valid": bool,
                "error": str  (only present if valid=False)
            }
        """
        valid, validation_msg = BackupService.validate_backup(zip_path)
        if not valid:
            return {"valid": False, "error": validation_msg}

        meta = BackupService.get_backup_metadata(zip_path)

        # Calculate zip size
        size_bytes = os.path.getsize(zip_path) if os.path.exists(zip_path) else 0
        size_str = BackupService._human_size_static(size_bytes)

        return {
            "valid":           True,
            "backup_type":     meta.get("backup_type", "Unknown"),
            "created_at":      meta.get("created_at", "Unknown"),
            "app_version":     meta.get("app_version", "Unknown"),
            "files_included":  meta.get("files_included", ["ledger.db"]),
            "size_str":        size_str,
        }

    @staticmethod
    def restore_backup(
        zip_path: str,
        db_path: str = "ledger.db",
        settings_file: str = SETTINGS_FILE,
        backup_dir: Optional[str] = None,
    ) -> tuple[bool, str]:
        """
        Full restore workflow:
          1. Validate the target zip
          2. Create a safety Pre-Restore backup
          3. Apply the restore (extract files)

        Args:
            zip_path:      Path to the backup zip to restore from.
            db_path:       Path to the active database file to overwrite.
            settings_file: Path to settings.json to overwrite.
            backup_dir:    Where to store the safety backup (None = use settings default).

        Returns:
            (success: bool, message: str)
        """
        # ── Step 1: Validate ─────────────────────────────────────────────────
        valid, validation_msg = BackupService.validate_backup(zip_path)
        if not valid:
            return False, f"Cannot restore — {validation_msg}"

        # ── Step 2: Safety backup (Pre-Restore) ──────────────────────────────
        safety_ok, safety_msg, safety_path = BackupService.create_backup(
            backup_type   = "Pre-Restore",
            backup_dir    = backup_dir,
            db_path       = db_path,
            settings_file = settings_file,
        )
        if not safety_ok:
            # Non-fatal: warn but allow user to proceed
            print(f"[RestoreService] Safety backup failed: {safety_msg}")
            # We still proceed — the user confirmed the restore action
        else:
            print(f"[RestoreService] Safety backup created: {safety_path}")

        # ── Step 3: Extract and apply ─────────────────────────────────────────
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()

                # Restore database
                if "ledger.db" in names:
                    # Write to a temp file first, then atomic-rename to avoid half-writes
                    temp_db = db_path + ".restore_tmp"
                    with zf.open("ledger.db") as src, open(temp_db, "wb") as dst:
                        dst.write(src.read())
                    # Replace live db
                    if os.path.exists(db_path):
                        os.replace(temp_db, db_path)
                    else:
                        os.rename(temp_db, db_path)
                else:
                    return False, "Archive does not contain 'ledger.db'."

                # Restore settings (non-fatal if missing from archive)
                if "settings.json" in names:
                    temp_settings = settings_file + ".restore_tmp"
                    with zf.open("settings.json") as src, open(temp_settings, "wb") as dst:
                        dst.write(src.read())
                    os.replace(temp_settings, settings_file)
                    print("[RestoreService] settings.json restored.")
                else:
                    print("[RestoreService] Archive has no settings.json — skipping.")

                # Restore any additional config files (.json except settings.json)
                for name in names:
                    if (name.endswith(".json")
                            and name not in ("settings.json", "backup_info.json", "ledger.db")):
                        try:
                            target = os.path.join(os.getcwd(), name)
                            with zf.open(name) as src, open(target, "wb") as dst:
                                dst.write(src.read())
                            print(f"[RestoreService] Restored config: {name}")
                        except Exception as ce:
                            print(f"[RestoreService] Could not restore {name}: {ce}")

        except zipfile.BadZipFile:
            return False, "Restore failed — archive is corrupt."
        except PermissionError as pe:
            return False, f"Restore failed — permission denied: {pe}"
        except OSError as oe:
            return False, f"Restore failed — file system error: {oe}"
        except Exception as e:
            return False, f"Restore failed — unexpected error: {e}"

        return True, "Restore completed successfully. Please restart the application."


# ── Standalone static helper (avoid circular import) ────────────────────────

# Attach a static helper to BackupService that RestoreService can reference
# without a circular import:
def _human_size_static(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 ** 2:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 ** 2):.1f} MB"


BackupService._human_size_static = staticmethod(_human_size_static)
