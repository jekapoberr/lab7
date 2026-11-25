import os
import sys
import sqlite3
from abc import ABC, abstractmethod

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))


class IDatabase(ABC):
    @abstractmethod
    def execute_query(self, query, params=()): pass

    @abstractmethod
    def fetch_all(self, query, params=()): pass

    @abstractmethod
    def fetch_one(self, query, params=()): pass


class DatabaseManager(IDatabase):
    def __init__(self, db_name="magazin.db"):
        if not os.path.isabs(db_name):
            db_name = os.path.join(APP_DIR, db_name)
        self.db_name = db_name
        self._create_tables()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_tables(self):
        query = """
        CREATE TABLE IF NOT EXISTS produse (
            item_id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            nume TEXT NOT NULL,
            pret REAL NOT NULL,
            arie REAL,
            is_inverter INTEGER,
            has_wifi INTEGER,
            volum REAL,
            is_nofrost INTEGER,
            are_dozator INTEGER,
            capacitate REAL,
            rpm INTEGER,
            is_smart INTEGER,
            image_path TEXT,
            image_orig_name TEXT
        )
        """
        self.execute_query(query)

        # Совместимость со старой базой magazin.db
        for col in ("image_path TEXT", "image_orig_name TEXT"):
            try:
                self.execute_query(f"ALTER TABLE produse ADD COLUMN {col}")
            except sqlite3.OperationalError:
                pass

    def execute_query(self, query, params=()):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()

    def fetch_all(self, query, params=()):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    def fetch_one(self, query, params=()):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()