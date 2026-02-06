import sqlite3
import os


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    # ======================================================
    # EMPLOYEES
    # ======================================================

    def get_employees(self):
        return self.conn.execute(
            "SELECT * FROM employees ORDER BY name"
        ).fetchall()

    def add_employee(self, name, rate, bank=None, iban=None, bic=None):
        self.conn.execute(
            """
            INSERT INTO employees (name, rate, bank, iban, bic)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, rate, bank, iban, bic)
        )
        self.conn.commit()

    def update_employee(self, emp_id, name, rate, bank=None, iban=None, bic=None):
        self.conn.execute(
            """
            UPDATE employees
            SET name=?, rate=?, bank=?, iban=?, bic=?
            WHERE id=?
            """,
            (name, rate, bank, iban, bic, emp_id)
        )
        self.conn.commit()

    def delete_employee(self, emp_id):
        self.conn.execute(
            "DELETE FROM employees WHERE id=?",
            (emp_id,)
        )
        self.conn.commit()

    # ======================================================
    # CLOSE
    # ======================================================

    def close(self):
        self.conn.close()
