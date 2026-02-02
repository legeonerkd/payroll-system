import sqlite3
from pathlib import Path


class Database:
    def __init__(self, db_path: str | Path = "salary.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()
        self._init_db()

    # ==================================================
    # INIT
    # ==================================================
    def _init_db(self):
        self.cur.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                rate REAL NOT NULL,
                has_bank_account INTEGER DEFAULT 0,
                bank_name TEXT,
                iban TEXT,
                bic TEXT
            )
            """
        )

        self.cur.execute(
            """
            CREATE TABLE IF NOT EXISTS work_hours (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                work_date TEXT NOT NULL,
                hours REAL NOT NULL,
                UNIQUE(employee_id, work_date),
                FOREIGN KEY(employee_id) REFERENCES employees(id)
            )
            """
        )

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
            (name, rate),
        )
        self.conn.commit()

    def delete_employee(self, emp_id: int):
        self.cur.execute(
            "DELETE FROM employees WHERE id=?",
            (emp_id,),
        )
        self.cur.execute(
            "DELETE FROM work_hours WHERE employee_id=?",
            (emp_id,),
        )
        self.conn.commit()

    def update_employee_name(self, emp_id: int, name: str):
        self.cur.execute(
            "UPDATE employees SET name=? WHERE id=?",
            (name, emp_id),
        )
        self.conn.commit()

    def update_employee_rate(self, emp_id: int, rate: float):
        self.cur.execute(
            "UPDATE employees SET rate=? WHERE id=?",
            (rate, emp_id),
        )
        self.conn.commit()

    def update_employee_bank(
        self,
        emp_id: int,
        has_bank: bool,
        bank_name: str,
        iban: str,
        bic: str,
    ):
        self.cur.execute(
            """
            UPDATE employees
            SET has_bank_account=?,
                bank_name=?,
                iban=?,
                bic=?
            WHERE id=?
            """,
            (
                int(has_bank),
                bank_name,
                iban,
                bic,
                emp_id,
            ),
        )
        self.conn.commit()

    # ==================================================
    # HOURS
    # ==================================================
    def load_hours(self, emp_id: int, start: str, end: str):
        return self.cur.execute(
            """
            SELECT work_date, hours
            FROM work_hours
            WHERE employee_id=?
              AND work_date BETWEEN ? AND ?
            ORDER BY work_date
            """,
            (emp_id, start, end),
        ).fetchall()

    def save_hours(self, emp_id: int, date: str, hours: float):
        self.cur.execute(
            """
            INSERT INTO work_hours (employee_id, work_date, hours)
            VALUES (?, ?, ?)
            ON CONFLICT(employee_id, work_date)
            DO UPDATE SET hours=excluded.hours
            """,
            (emp_id, date, hours),
        )
        self.conn.commit()

    # ==================================================
    # CLOSE
    # ==================================================
    def close(self):
        try:
            self.conn.commit()
        except Exception:
            pass
        finally:
            self.conn.close()

