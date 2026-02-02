import sqlite3
from pathlib import Path


DB_VERSION = 2


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()
        self._init_db()

    # ==================================================
    # INIT / VERSIONING
    # ==================================================
    def _init_db(self):
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)

        version = self._get_version()

        if version == 0:
            self._create_schema_v1()
            self._set_version(1)
            version = 1

        if version == 1:
            self._migrate_1_to_2()
            self._set_version(2)

        self.conn.commit()

    def _get_version(self) -> int:
        row = self.cur.execute(
            "SELECT value FROM meta WHERE key='db_version'"
        ).fetchone()
        return int(row["value"]) if row else 0

    def _set_version(self, version: int):
        self.cur.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('db_version', ?)",
            (str(version),)
        )

    # ==================================================
    # SCHEMA v1 (SAFE)
    # ==================================================
    def _create_schema_v1(self):
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            rate REAL
        )
        """)

        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_hours (
            employee_id INTEGER,
            work_date TEXT,
            hours REAL,
            PRIMARY KEY (employee_id, work_date)
        )
        """)

    # ==================================================
    # MIGRATION v1 → v2 (SAFE)
    # ==================================================
    def _column_exists(self, table: str, column: str) -> bool:
        cols = self.cur.execute(f"PRAGMA table_info({table})").fetchall()
        return any(c["name"] == column for c in cols)

    def _migrate_1_to_2(self):
        if not self._column_exists("employees", "has_bank_account"):
            self.cur.execute(
                "ALTER TABLE employees ADD COLUMN has_bank_account INTEGER DEFAULT 0"
            )

        if not self._column_exists("employees", "bank_name"):
            self.cur.execute(
                "ALTER TABLE employees ADD COLUMN bank_name TEXT"
            )

        if not self._column_exists("employees", "iban"):
            self.cur.execute(
                "ALTER TABLE employees ADD COLUMN iban TEXT"
            )

        if not self._column_exists("employees", "bic"):
            self.cur.execute(
                "ALTER TABLE employees ADD COLUMN bic TEXT"
            )

    # ==================================================
    # EMPLOYEES
    # ==================================================
    def get_employees(self):
        return self.cur.execute(
            "SELECT * FROM employees ORDER BY name"
        ).fetchall()

    def add_employee(self, name: str, rate: float):
        self.cur.execute(
            "INSERT INTO employees (name, rate) VALUES (?, ?)",
            (name, rate)
        )
        self.conn.commit()

    def delete_employee(self, emp_id: int):
        self.cur.execute(
            "DELETE FROM employees WHERE id=?",
            (emp_id,)
        )
        self.conn.commit()

    def update_employee_bank(
        self,
        emp_id: int,
        has_bank: bool,
        bank: str,
        iban: str,
        bic: str,
    ):
        self.cur.execute("""
        UPDATE employees
        SET has_bank_account=?,
            bank_name=?,
            iban=?,
            bic=?
        WHERE id=?
        """, (int(has_bank), bank, iban, bic, emp_id))
        self.conn.commit()

    # ==================================================
    # HOURS
    # ==================================================
    def save_hours(self, emp_id: int, date_iso: str, hours: float):
        self.cur.execute("""
        INSERT OR REPLACE INTO daily_hours
        (employee_id, work_date, hours)
        VALUES (?, ?, ?)
        """, (emp_id, date_iso, hours))
        self.conn.commit()

    def load_hours(self, emp_id: int, start: str, end: str):
        return self.cur.execute("""
        SELECT work_date, hours
        FROM daily_hours
        WHERE employee_id=?
          AND work_date BETWEEN ? AND ?
        ORDER BY work_date
        """, (emp_id, start, end)).fetchall()

    # ==================================================
    def close(self):
        self.conn.close()
