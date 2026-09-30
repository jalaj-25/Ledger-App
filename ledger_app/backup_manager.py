"""
backup_manager.py
=================
BackupManager — Orchestrator for Jalaj Ledger Backup & Recovery System.

Wires together BackupService + RestoreService and provides high-level hooks:
  - trigger_shutdown_backup()       — called by app.py on_close()
  - trigger_daily_backup_if_needed()— called at startup (checks 24-hour threshold)
  - trigger_manual_backup()         — user-initiated from Settings UI
  - trigger_pre_operation_backup()  — called before destructive operations

All operations run safely; no unhandled exceptions escape.
Sends Windows toast notifications via the injected NotificationService.
"""

import os
import json
import datetime
import threading
from typing import Optional, Callable

from ledger_app.services.backup_service import BackupService
from ledger_app.services.restore_service import RestoreService

SETTINGS_FILE = "settings.json"
DAILY_BACKUP_INTERVAL_HOURS = 24


class BackupManager:
    """
    Singleton-style orchestrator that coordinates all backup operations.

    Usage in app.py:
        self.backup_manager = BackupManager()
        self.backup_manager.initialize(
            db_path="ledger.db",
            settings_file="settings.json",
            notification_service=self.notification_service
        )
    """

    def __init__(self):
        self.db_path: str = "ledger.db"
        self.settings_file: str = SETTINGS_FILE
        self.notification_service = None
        self._initialized = False
        self._lock = threading.Lock()

    # ── Initialization ───────────────────────────────────────────────────────

    def initialize(
        self,
        db_path: str = "ledger.db",
        settings_file: str = SETTINGS_FILE,
        notification_service=None,
    ):
        """
        Wires up the manager with runtime paths and the notification service.
        Call this once after App.__init__ sets up services.
        """
        self.db_path = db_path
        self.settings_file = settings_file
        self.notification_service = notification_service
        self._initialized = True
        print("[BackupManager] Initialized.")

    # ── Public API ───────────────────────────────────────────────────────────

    def trigger_manual_backup(self) -> tuple[bool, str]:
        """
        User-initiated backup from Settings UI.
        Runs synchronously (on calling thread) so the UI can show immediate feedback.

        Returns:
            (success: bool, message: str)
        """
        return self._run_backup("Manual", notify=True)

    def trigger_shutdown_backup(self) -> tuple[bool, str]:
        """
        Called by app.py on_close() before destroy().
        Checks `auto_backup_enabled` in settings — skips if disabled.
        Runs synchronously to complete before app exits.
        """
        if not self._is_auto_backup_enabled():
            print("[BackupManager] Shutdown backup skipped (auto_backup_enabled=false).")
            return True, "Auto backup disabled — skipped."
        return self._run_backup("Shutdown", notify=False)

    def trigger_daily_backup_if_needed(self, on_complete: Optional[Callable] = None):
        """
        Checks if more than 24 hours have elapsed since the last backup.
        If so, creates an Automatic backup in a background thread.

        Args:
            on_complete: Optional callback(success, message) called after completion.
        """
        if not self._is_auto_backup_enabled():
            print("[BackupManager] Daily backup skipped (auto_backup_enabled=false).")
            return

        if not self._daily_backup_due():
            print("[BackupManager] Daily backup not due yet — skipping.")
            return

        print("[BackupManager] Daily backup due — starting background backup...")

        def _worker():
            success, msg = self._run_backup("Automatic", notify=True)
            if on_complete:
                try:
                    on_complete(success, msg)
                except Exception as e:
                    print(f"[BackupManager] on_complete callback error: {e}")

        thread = threading.Thread(target=_worker, daemon=True, name="BackupManager-Daily")
        thread.start()

    def trigger_pre_operation_backup(self, operation_label: str) -> tuple[bool, str]:
        """
        Creates a safety backup before a destructive operation.
        Runs synchronously so the operation is blocked until the backup completes.

        Args:
            operation_label: Human-readable name for the operation type.
                             Should be one of: "Pre-Restore", "Pre-Delete"
        Returns:
            (success: bool, message: str)
        """
        # Map label to valid backup type
        valid_types = {"Pre-Restore", "Pre-Delete"}
        btype = operation_label if operation_label in valid_types else "Pre-Delete"
        success, msg, _ = self._create_backup_internal(btype)
        return success, msg

    def get_backup_history(self) -> list:
        """Returns the list of BackupInfo objects from the backup directory."""
        backup_dir = BackupService.get_backup_dir(self.settings_file)
        return BackupService.get_backup_history(backup_dir)

    def get_backup_dir(self) -> str:
        """Returns the current backup directory path."""
        return BackupService.get_backup_dir(self.settings_file)

    def get_last_backup_info(self) -> dict:
        """
        Returns a dict with last backup metadata from settings.json:
          { "last_backup_date": str, "last_backup_type": str }
        """
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return {
                    "last_backup_date": data.get("last_backup_date", "Never"),
                    "last_backup_type": data.get("last_backup_type", "—"),
                }
        except Exception as e:
            print(f"[BackupManager] Could not read last backup info: {e}")
        return {"last_backup_date": "Never", "last_backup_type": "—"}

    def set_backup_folder(self, folder_path: str) -> tuple[bool, str]:
        """
        Saves a new custom backup folder to settings.json.
        Returns (success, message).
        """
        try:
            data: dict = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data["backup_folder"] = folder_path
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True, f"Backup folder updated to: {folder_path}"
        except Exception as e:
            return False, f"Could not save backup folder: {e}"

    def set_auto_backup_enabled(self, enabled: bool) -> bool:
        """Persists auto_backup_enabled flag to settings.json. Returns success."""
        try:
            data: dict = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data["auto_backup_enabled"] = enabled
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"[BackupManager] Could not save auto_backup_enabled: {e}")
            return False

    def is_auto_backup_enabled(self) -> bool:
        """Public wrapper for the auto-backup enabled check."""
        return self._is_auto_backup_enabled()

    # ── Private helpers ──────────────────────────────────────────────────────

    def _run_backup(self, backup_type: str, notify: bool = True) -> tuple[bool, str]:
        """Internal synchronous backup runner with notification dispatch."""
        with self._lock:
            success, msg, zip_path = self._create_backup_internal(backup_type)

        if notify:
            self._notify(success, msg, backup_type)

        return success, msg

    def _create_backup_internal(self, backup_type: str) -> tuple[bool, str, Optional[str]]:
        """Wraps BackupService.create_backup with path resolution."""
        backup_dir = BackupService.get_backup_dir(self.settings_file)
        return BackupService.create_backup(
            backup_type   = backup_type,
            backup_dir    = backup_dir,
            db_path       = self.db_path,
            settings_file = self.settings_file,
        )

    def _notify(self, success: bool, message: str, backup_type: str):
        """Dispatches a desktop notification if notification_service is available."""
        if not self.notification_service:
            return
        try:
            if success:
                title = f"✅ Backup Created ({backup_type})"
            else:
                title = f"❌ Backup Failed ({backup_type})"
            self.notification_service.send_notification(title, message)
        except Exception as e:
            print(f"[BackupManager] Notification dispatch failed: {e}")

    def _is_auto_backup_enabled(self) -> bool:
        """Reads auto_backup_enabled from settings.json. Defaults to True."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return bool(data.get("auto_backup_enabled", True))
        except Exception:
            pass
        return True

    def _daily_backup_due(self) -> bool:
        """Returns True if last backup was more than 24 hours ago (or never)."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                last_str = data.get("last_backup_date", "")
                if not last_str or last_str == "Never":
                    return True
                last_dt = datetime.datetime.strptime(last_str, "%Y-%m-%d %H:%M:%S")
                elapsed = datetime.datetime.now() - last_dt
                return elapsed.total_seconds() >= DAILY_BACKUP_INTERVAL_HOURS * 3600
        except Exception as e:
            print(f"[BackupManager] Error checking daily backup threshold: {e}")
        return True  # If uncertain, perform the backup
