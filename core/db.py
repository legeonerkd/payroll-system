import sqlite3
from pathlib import Path


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()
        self._init_schema()

    # ==================================================
    def _init_schema(self):
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            rate REAL NOT NULL,
            has_bank_account INTEGER DEFAULT 0,
            bank_name TEXT,
            iban TEXT,
            bic TEXT
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

        self.conn.commit()

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
        SET has_bank_account = ?,
            bank_name = ?,
            iban = ?,
            bic = ?
        WHERE id = ?
        """, (
            int(has_bank),
            bank,
            iban,
            bic,
            emp_id
        ))
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

