"""
session_manager.py
------------------
Singleton that holds the currently authenticated User for the lifetime
of the application session.

Design:
  - Stateless from the UI perspective: screens call SessionManager.get_current_user()
    and check permissions via user.has_permission(...)
  - Inactivity tracking: the App shell calls SessionManager.touch() on any user
    interaction; it calls SessionManager.is_expired() on a periodic timer.
"""

import time
from typing import Optional
from ledger_app.models.user import User

# Default inactivity timeout in seconds (30 minutes)
DEFAULT_TIMEOUT_SECONDS = 30 * 60


class SessionManager:
    """Thread-safe singleton session store."""

    _current_user:    Optional[User] = None
    _last_activity:   float          = 0.0
    _timeout_seconds: int            = DEFAULT_TIMEOUT_SECONDS
    _pin_unlocked:    bool           = False   # True after first password login in this session

    # ── Session Lifecycle ─────────────────────────────────────────────────────

    @classmethod
    def start_session(cls, user: User) -> None:
        cls._current_user    = user
        cls._last_activity   = time.time()
        cls._pin_unlocked    = True

    @classmethod
    def end_session(cls) -> None:
        cls._current_user  = None
        cls._last_activity = 0.0
        cls._pin_unlocked  = False

    @classmethod
    def lock_session(cls) -> None:
        """Locks without clearing user — re-authentication needed (PIN or password)."""
        cls._last_activity = 0.0

    # ── Activity Tracking ─────────────────────────────────────────────────────

    @classmethod
    def touch(cls) -> None:
        """Reset inactivity timer. Call this on every significant user interaction."""
        if cls._current_user is not None:
            cls._last_activity = time.time()

    @classmethod
    def is_expired(cls) -> bool:
        """Returns True if inactivity timeout has been exceeded."""
        if cls._current_user is None:
            return False
        if cls._last_activity == 0.0:
            return True
        return (time.time() - cls._last_activity) > cls._timeout_seconds

    # ── Configuration ─────────────────────────────────────────────────────────

    @classmethod
    def set_timeout(cls, minutes: int) -> None:
        cls._timeout_seconds = max(1, minutes) * 60

    @classmethod
    def get_timeout_minutes(cls) -> int:
        return cls._timeout_seconds // 60

    # ── State Queries ─────────────────────────────────────────────────────────

    @classmethod
    def is_logged_in(cls) -> bool:
        return cls._current_user is not None

    @classmethod
    def get_current_user(cls) -> Optional[User]:
        return cls._current_user

    @classmethod
    def has_permission(cls, permission: str) -> bool:
        user = cls._current_user
        if user is None:
            return False
        return user.has_permission(permission)

    @classmethod
    def is_pin_unlocked(cls) -> bool:
        """True if user has completed a full password login in this session."""
        return cls._pin_unlocked

    @classmethod
    def is_owner(cls) -> bool:
        user = cls._current_user
        return user is not None and user.is_owner
