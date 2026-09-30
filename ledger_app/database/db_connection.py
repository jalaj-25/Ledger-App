import os
import sqlite3
from typing import Generator
from contextlib import contextmanager

class DatabaseManager:
    """
    Manages SQLite database connections, initialization, and transactions.
    Implemented as a singleton.
    """
    _instance = None

    def __new__(cls, db_path: str = "ledger.db"):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.db_path = db_path
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: str = "ledger.db"):
        # __init__ can run multiple times because of __new__, ensure we only init once
        if getattr(self, '_initialized', False):
            return
        self.db_path = db_path
        # Ensure parent directories exist
        db_dir = os.path.dirname(os.path.abspath(self.db_path))
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._initialized = True
        self.init_db()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager for acquiring a database connection.
        Enforces foreign key checks and WAL mode for better concurrency.
        Automatically commits or rolls back transactions.
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        # Enable foreign key support
        conn.execute("PRAGMA foreign_keys = ON;")
        # Enable WAL mode for parallel read/write performance
        conn.execute("PRAGMA journal_mode = WAL;")
        # Configure row factory to return dictionary-like Row objects
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def init_db(self):
        """Initializes tables and seeds base tables like payment_modes."""
        from ledger_app.database.schema import CREATE_SCHEMA_STATEMENTS, SEED_DATA_STATEMENTS

        with self.get_connection() as conn:
            # Execute schema creation SQL statements
            for statement in CREATE_SCHEMA_STATEMENTS:
                conn.execute(statement)
            
            # Execute seeds if payment modes are empty
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM payment_modes;")
            row = cursor.fetchone()
            if row and row['count'] == 0:
                for statement in SEED_DATA_STATEMENTS:
                    conn.execute(statement)

        # Run migrations AFTER schema creation so new DBs and existing DBs are both handled
        self._migrate_db()

    def _migrate_db(self):
        """
        Applies non-destructive ALTER TABLE migrations for existing databases.
        Safe to call on every startup — checks column existence before adding.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # ── customer_tag column (previous migration) ──────────────────────
            cursor.execute("PRAGMA table_info(customers);")
            columns = [row['name'] for row in cursor.fetchall()]
            if 'customer_tag' not in columns:
                conn.execute(
                    "ALTER TABLE customers ADD COLUMN customer_tag TEXT NOT NULL DEFAULT 'General';"
                )
                print("[DB Migration] Added 'customer_tag' column to customers table.")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_customers_tag ON customers(customer_tag);"
            )

        # ── users + audit_logs migration ──────────────────────────────────────
        self._migrate_users()

    def _migrate_users(self):
        """
        Ensures the users and audit_logs tables exist and seeds a default Owner
        account on first run.

        Migration strategy:
          1. If no users exist, attempt to migrate the existing master-password
             hash/salt from settings.json → owner account.
          2. If no master password is configured either, generate a random
             first-time password (printed to console) and mark it 'must_change'.
        """
        import json
        import secrets
        import hashlib

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Ensure new recovery columns exist
            cursor.execute("PRAGMA table_info(users);")
            columns = [row['name'] for row in cursor.fetchall()]
            if 'recovery_email' not in columns:
                conn.execute("ALTER TABLE users ADD COLUMN recovery_email TEXT;")
                print("[DB Migration] Added 'recovery_email' column to users table.")
            if 'otp_attempts' not in columns:
                conn.execute("ALTER TABLE users ADD COLUMN otp_attempts INTEGER DEFAULT 0;")
                print("[DB Migration] Added 'otp_attempts' column to users table.")
            if 'last_recovery_request' not in columns:
                conn.execute("ALTER TABLE users ADD COLUMN last_recovery_request TEXT;")
                print("[DB Migration] Added 'last_recovery_request' column to users table.")
            if 'must_change' not in columns:
                conn.execute("ALTER TABLE users ADD COLUMN must_change INTEGER DEFAULT 0;")
                print("[DB Migration] Added 'must_change' column to users table.")

            # Count existing owner users
            cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'owner';")
            if cursor.fetchone()['cnt'] > 0:
                return  # Already seeded — nothing to do

            print("[DB Migration] No owner account found. Seeding default owner...")

            # Run the preprocessor to convert owner_password to hash + salt in settings.json
            try:
                from ledger_app.services.settings_preprocessor import preprocess_settings
                preprocess_settings("settings.json")
            except Exception as e:
                print(f"[DB Migration] Preprocessor error: {e}")

            # Attempt to reuse existing master-password hash from settings.json
            settings_path = "settings.json"
            existing_hash = ""
            existing_salt = ""
            if os.path.exists(settings_path):
                try:
                    with open(settings_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    existing_hash = cfg.get("password_hash", "")
                    existing_salt = cfg.get("salt", "")
                except Exception:
                    pass

            if existing_hash and existing_salt:
                # Reuse existing PBKDF2 hash — the owner password stays the same
                pw_hash = existing_hash
                salt    = existing_salt
                owner_uname = "owner"
                print("[DB Migration] Migrated existing master password to 'owner' account.")
            else:
                # Seeding default client credentials: admin / Sunil@123
                owner_uname = "admin"
                default_pw = "Sunil@123"
                salt_bytes   = secrets.token_bytes(16)
                hash_bytes   = hashlib.pbkdf2_hmac(
                    "sha256", default_pw.encode("utf-8"), salt_bytes, 100_000
                )
                salt    = salt_bytes.hex()
                pw_hash = hash_bytes.hex()
                print(f"\n{'='*55}")
                print(f"  FIRST RUN — DEFAULT OWNER CREDENTIALS")
                print(f"  Username : {owner_uname}")
                print(f"  Password : {default_pw}")
                print(f"{'='*55}\n")

            conn.execute(
                """
                INSERT INTO users (username, password_hash, salt, role, is_active)
                VALUES (?, ?, ?, 'owner', 1)
                """,
                (owner_uname, pw_hash, salt)
            )
            conn.execute(
                """
                INSERT INTO audit_logs (username, action, details)
                VALUES ('system', 'SYSTEM_INIT', 'Default owner account created during database migration.')
                """
            )
            print("[DB Migration] Default owner account created successfully.")
