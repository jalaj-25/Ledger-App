from ledger_app.database.db_connection import DatabaseManager

class BaseRepository:
    """Base repository wrapper containing shared database reference access."""
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
