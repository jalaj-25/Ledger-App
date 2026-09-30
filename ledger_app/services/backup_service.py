"""
backup_service.py
=================
Core Backup Engine for Jalaj Ledger Management System.

Responsibilities:
  - Create compressed .zip backup packages (db + settings + extra configs)
  - Embed backup metadata (backup_info.json) inside every zip
  - Query backup history from a directory
  - Enforce retention policy (keep last N backups)
  - Validate backup archives for integrity

Backup Format:
  backups/
  └── ledger_backup_2026-06-16_09-18-57_manual.zip
      ├── ledger.db
      ├── settings.json
      └── backup_info.json
"""

import os
import json
import shutil
import zipfile
import datetime
from typing import Optional

# ── Type suffix mapping ──────────────────────────────────────────────────────
BACKUP_TYPE_SUFFIXES = {
    "Manual":      "manual",
    "Automatic":   "auto",
    "Shutdown":    "shutdown",
    "Pre-Restore": "prerestore",
    "Pre-Delete":  "predelete",
}

APP_VERSION = "v1.1.0"
SETTINGS_FILE = "settings.json"
DEFAULT_BACKUP_DIR = "backups"
RETENTION_LIMIT = 30


class BackupInfo:
    """Structured representation of a single backup entry."""
    __slots__ = ("file_name", "file_path", "created_at", "size_bytes", "size_str", "backup_type")

    def __init__(self, file_name: str, file_path: str, created_at: datetime.datetime,
                 size_bytes: int, backup_type: str):
        self.file_name   = file_name
        self.file_path   = file_path
        self.created_at  = created_at
        self.size_bytes  = size_bytes
        self.size_str    = self._human_size(size_bytes)
        self.backup_type = backup_type

    @staticmethod
    def _human_size(n: int) -> str:
        if n < 1024:
            return f"{n} B"
        if n < 1024 ** 2:
            return f"{n / 1024:.1f} KB"
        return f"{n / (1024 ** 2):.1f} MB"

    def to_dict(self) -> dict:
        return {
            "file_name":   self.file_name,
            "file_path":   self.file_path,
            "created_at":  self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "size_str":    self.size_str,
            "size_bytes":  self.size_bytes,
            "backup_type": self.backup_type,
        }


class BackupService:
    """
    Low-level backup engine.
    All public methods return (success: bool, message: str) tuples to prevent crashes.
    """

    # ── Directory helpers ────────────────────────────────────────────────────

    @staticmethod
    def get_backup_dir(settings_file: str = SETTINGS_FILE) -> str:
        """
        Reads `backup_folder` from settings.json.
        Falls back to `backups/` relative to CWD if missing or unreadable.
        """
        try:
            if os.path.exists(settings_file):
                with open(settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                folder = data.get("backup_folder", DEFAULT_BACKUP_DIR)
                if folder and isinstance(folder, str):
                    return folder
        except Exception as e:
            print(f"[BackupService] Could not read backup_folder from settings: {e}")
        return DEFAULT_BACKUP_DIR

    @staticmethod
    def ensure_backup_dir(backup_dir: str) -> tuple[bool, str]:
        """Creates the backup directory if it does not exist."""
        try:
            os.makedirs(backup_dir, exist_ok=True)
            return True, backup_dir
        except PermissionError:
            return False, f"Permission denied creating backup folder: {backup_dir}"
        except OSError as e:
            return False, f"Cannot create backup folder '{backup_dir}': {e}"

    # ── Backup creation ──────────────────────────────────────────────────────

    @staticmethod
    def create_backup(
        backup_type: str,
        backup_dir: Optional[str] = None,
        db_path: str = "ledger.db",
        settings_file: str = SETTINGS_FILE,
    ) -> tuple[bool, str, Optional[str]]:
        """
        Creates a compressed zip backup package.

        Args:
            backup_type: One of "Manual", "Automatic", "Shutdown",
                         "Pre-Restore", "Pre-Delete"
            backup_dir:  Target folder. None = read from settings / default.
            db_path:     Path to the active SQLite database.
            settings_file: Path to settings.json.

        Returns:
            (success: bool, message: str, zip_path: Optional[str])
        """
        # Resolve backup directory
        resolved_dir = backup_dir or BackupService.get_backup_dir(settings_file)
        ok, result = BackupService.ensure_backup_dir(resolved_dir)
        if not ok:
            return False, result, None

        # Build file name
        now = datetime.datetime.now()
        ts  = now.strftime("%Y-%m-%d_%H-%M-%S")
        suffix = BACKUP_TYPE_SUFFIXES.get(backup_type, "manual")
        zip_name = f"ledger_backup_{ts}_{suffix}.zip"
        zip_path = os.path.join(resolved_dir, zip_name)

        # Collect files to include
        files_to_backup: list[tuple[str, str]] = []  # (source_path, archive_name)

        if os.path.exists(db_path):
            files_to_backup.append((db_path, "ledger.db"))
        else:
            return False, f"Database not found at: {db_path}", None

        if os.path.exists(settings_file):
            files_to_backup.append((settings_file, "settings.json"))

        # Include any additional *.json config files in CWD (future-proof)
        cwd = os.path.dirname(os.path.abspath(settings_file)) if settings_file != "settings.json" else os.getcwd()
        for fname in os.listdir(cwd):
            if (fname.endswith(".json")
                    and fname != "settings.json"
                    and fname not in {os.path.basename(p) for p, _ in files_to_backup}):
                full = os.path.join(cwd, fname)
                if os.path.isfile(full):
                    files_to_backup.append((full, fname))

        # Build embedded metadata
        metadata = {
            "backup_type":   backup_type,
            "created_at":    now.strftime("%Y-%m-%d %H:%M:%S"),
            "app_version":   APP_VERSION,
            "db_file":       "ledger.db",
            "settings_file": "settings.json",
            "files_included": [arc for _, arc in files_to_backup],
        }

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                # Write data files
                for src, arc_name in files_to_backup:
                    zf.write(src, arc_name)

                # Write embedded manifest
                zf.writestr("backup_info.json", json.dumps(metadata, indent=2))

        except PermissionError:
            return False, f"Permission denied writing backup to: {zip_path}", None
        except OSError as e:
            # Disk-full or other I/O errors
            _safe_remove(zip_path)
            if "No space left" in str(e) or "28" in str(e):
                return False, "Backup failed: Disk is full. Please free up disk space.", None
            return False, f"Backup failed (I/O error): {e}", None
        except Exception as e:
            _safe_remove(zip_path)
            return False, f"Unexpected error during backup: {e}", None

        # Update settings.json with last backup metadata
        BackupService._record_backup_in_settings(
            settings_file, now.strftime("%Y-%m-%d %H:%M:%S"), backup_type
        )

        # Enforce retention
        BackupService.enforce_retention(resolved_dir)

        size_str = BackupInfo._human_size(os.path.getsize(zip_path))
        return True, f"Backup created: {zip_name} ({size_str})", zip_path

    # ── Retention ────────────────────────────────────────────────────────────

    @staticmethod
    def enforce_retention(
        backup_dir: str,
        max_count: int = RETENTION_LIMIT,
    ) -> tuple[int, list[str]]:
        """
        Deletes the oldest backups so at most `max_count` remain.

        Returns:
            (deleted_count, list_of_deleted_names)
        """
        backups = BackupService.get_backup_history(backup_dir)
        if len(backups) <= max_count:
            return 0, []

        # backups are sorted newest-first; drop oldest
        to_delete = backups[max_count:]
        deleted_names: list[str] = []
        for b in to_delete:
            try:
                os.remove(b.file_path)
                deleted_names.append(b.file_name)
                print(f"[BackupService] Retention: removed {b.file_name}")
            except Exception as e:
                print(f"[BackupService] Could not remove {b.file_name}: {e}")

        return len(deleted_names), deleted_names

    # ── History ──────────────────────────────────────────────────────────────

    @staticmethod
    def get_backup_history(backup_dir: str) -> list[BackupInfo]:
        """
        Scans backup_dir for ledger_backup_*.zip files.
        Returns a list sorted newest-first.
        """
        history: list[BackupInfo] = []

        if not os.path.isdir(backup_dir):
            return history

        try:
            for fname in os.listdir(backup_dir):
                if not (fname.startswith("ledger_backup_") and fname.endswith(".zip")):
                    continue
                fpath = os.path.join(backup_dir, fname)
                if not os.path.isfile(fpath):
                    continue

                size_bytes = os.path.getsize(fpath)
                created_at, btype = BackupService._parse_backup_filename(fname)
                if created_at is None:
                    # Fall back to filesystem mtime
                    created_at = datetime.datetime.fromtimestamp(os.path.getmtime(fpath))

                # Try to read embedded backup_info.json for accurate type
                btype = BackupService._read_embedded_type(fpath) or btype

                history.append(BackupInfo(
                    file_name   = fname,
                    file_path   = fpath,
                    created_at  = created_at,
                    size_bytes  = size_bytes,
                    backup_type = btype,
                ))
        except Exception as e:
            print(f"[BackupService] Error scanning backup directory: {e}")

        # Sort newest first
        history.sort(key=lambda b: b.created_at, reverse=True)
        return history

    # ── Validation ───────────────────────────────────────────────────────────

    @staticmethod
    def validate_backup(zip_path: str) -> tuple[bool, str]:
        """
        Checks that a zip file:
          1. Exists and is a valid zip archive
          2. Contains ledger.db
        Returns (valid: bool, message: str)
        """
        if not os.path.exists(zip_path):
            return False, "Backup file not found."

        if not zipfile.is_zipfile(zip_path):
            return False, "File is not a valid zip archive (may be corrupt)."

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                if "ledger.db" not in names:
                    return False, "Backup archive is missing 'ledger.db'. Cannot restore."
                # Test CRC of all entries
                bad = zf.testzip()
                if bad:
                    return False, f"Corrupt entry detected in archive: {bad}"
        except zipfile.BadZipFile:
            return False, "Backup archive is corrupt (BadZipFile)."
        except Exception as e:
            return False, f"Backup validation error: {e}"

        return True, "Backup is valid."

    # ── Metadata helpers ─────────────────────────────────────────────────────

    @staticmethod
    def get_backup_metadata(zip_path: str) -> dict:
        """Reads and returns the embedded backup_info.json from a zip, or {}."""
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                if "backup_info.json" in zf.namelist():
                    return json.loads(zf.read("backup_info.json").decode("utf-8"))
        except Exception as e:
            print(f"[BackupService] Could not read backup metadata from {zip_path}: {e}")
        return {}

    # ── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _record_backup_in_settings(settings_file: str, timestamp: str, backup_type: str):
        """Updates last_backup_date and last_backup_type in settings.json."""
        data: dict = {}
        try:
            if os.path.exists(settings_file):
                with open(settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
        except Exception:
            pass
        data["last_backup_date"] = timestamp
        data["last_backup_type"] = backup_type
        try:
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"[BackupService] Could not update last_backup_date in settings: {e}")

    @staticmethod
    def _parse_backup_filename(fname: str) -> tuple[Optional[datetime.datetime], str]:
        """
        Parses `ledger_backup_YYYY-MM-DD_HH-MM-SS_type.zip`.
        Returns (datetime, type_string) or (None, "Unknown").
        """
        # Strip prefix and suffix
        stem = fname.replace("ledger_backup_", "").replace(".zip", "")
        parts = stem.split("_")
        # parts: ['2026-06-16', '09-18-57', 'manual']  (3 parts) or 2 (legacy)
        try:
            if len(parts) >= 2:
                dt = datetime.datetime.strptime(f"{parts[0]}_{parts[1]}", "%Y-%m-%d_%H-%M-%S")
                # Reverse-map suffix to type label
                suffix = parts[2] if len(parts) >= 3 else ""
                rev_map = {v: k for k, v in BACKUP_TYPE_SUFFIXES.items()}
                btype = rev_map.get(suffix, "Manual")
                return dt, btype
        except Exception:
            pass
        return None, "Manual"

    @staticmethod
    def _read_embedded_type(zip_path: str) -> Optional[str]:
        """Fast read of backup_type from embedded backup_info.json."""
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                if "backup_info.json" in zf.namelist():
                    meta = json.loads(zf.read("backup_info.json").decode("utf-8"))
                    return meta.get("backup_type")
        except Exception:
            pass
        return None


# ── Module-level helper ──────────────────────────────────────────────────────

def _safe_remove(path: str):
    """Silently removes a file, ignoring errors."""
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
