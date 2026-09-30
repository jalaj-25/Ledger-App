CREATE_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL CHECK(length(name) >= 2),
        phone TEXT,
        address TEXT,
        notes TEXT,
        opening_balance REAL NOT NULL DEFAULT 0.0,
        customer_tag TEXT NOT NULL DEFAULT 'General',
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS payment_modes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mode_name TEXT UNIQUE NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        transaction_type TEXT NOT NULL CHECK(transaction_type IN ('CREDIT', 'DEBIT', 'DAILY_CHARGE')),
        amount REAL NOT NULL CHECK(amount >= 0.0),
        payment_mode_id INTEGER,
        description TEXT,
        transaction_date TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
        FOREIGN KEY (payment_mode_id) REFERENCES payment_modes(id) ON DELETE SET NULL
    );
    """,
    # Performance Indexes
    "CREATE INDEX IF NOT EXISTS idx_transactions_customer ON transactions(customer_id);",
    "CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date);",
    "CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name);",
    # ── Multi-User Auth Tables ────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
        password_hash TEXT    NOT NULL,
        salt          TEXT    NOT NULL,
        role          TEXT    NOT NULL DEFAULT 'staff' CHECK(role IN ('owner', 'staff')),
        pin_hash      TEXT,
        pin_salt      TEXT,
        is_active     INTEGER NOT NULL DEFAULT 1,
        created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
        last_login    TEXT,
        recovery_email TEXT,
        otp_attempts   INTEGER DEFAULT 0,
        last_recovery_request TEXT,
        must_change    INTEGER DEFAULT 0
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id   INTEGER,
        username  TEXT    NOT NULL DEFAULT 'system',
        action    TEXT    NOT NULL,
        details   TEXT,
        timestamp TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_audit_user     ON audit_logs(user_id);"
]

# Migration statements for upgrading existing databases (safe — IF NOT EXISTS equivalent via PRAGMA)
MIGRATION_STATEMENTS = [
    # Add customer_tag column if it doesn't already exist (SQLite doesn't support IF NOT EXISTS for ADD COLUMN)
    # Handled explicitly in db_connection.py via PRAGMA table_info
]

SEED_DATA_STATEMENTS = [
    "INSERT INTO payment_modes (mode_name) VALUES ('Cash');",
    "INSERT INTO payment_modes (mode_name) VALUES ('UPI / Online');",
    "INSERT INTO payment_modes (mode_name) VALUES ('Card');",
    "INSERT INTO payment_modes (mode_name) VALUES ('Bank Transfer');",
    "INSERT INTO payment_modes (mode_name) VALUES ('Cheque');"
]
