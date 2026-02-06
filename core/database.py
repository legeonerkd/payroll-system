import sqlite3
from datetime import datetime


class Database:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        cur = self.conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                rate REAL NOT NULL,
                bank TEXT,
                iban TEXT,
                bic TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS payrolls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                period_from TEXT NOT NULL,
                period_to TEXT NOT NULL,
                created_at TEXT NOT NULL,
                rate REAL NOT NULL,
                utilities REAL,
                rental REAL,
                total_hours REAL NOT NULL,
                net_amount REAL NOT NULL,
                FOREIGN KEY(employee_id) REFERENCES employees(id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS payroll_days (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payroll_id INTEGER NOT NULL,
                work_date TEXT NOT NULL,
                hours REAL NOT NULL,
                FOREIGN KEY(payroll_id) REFERENCES payrolls(id)
            )
        """)

        self.conn.commit()

    # ================= EMPLOYEES =================

    def get_employees(self):
        return self.conn.execute(
            "SELECT * FROM employees ORDER BY name"
        ).fetchall()

    # ================= PAYROLL SAVE =================

    def save_payroll(
        self, employee_id, period_from, period_to,
        rate, utilities, rental, total_hours, net_amount, days
    ):
        cur = self.conn.cursor()

        cur.execute("""
            INSERT INTO payrolls (
                employee_id, period_from, period_to, created_at,
                rate, utilities, rental, total_hours, net_amount
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            employee_id,
            period_from,
            period_to,
            datetime.now().strftime("%d-%m-%Y"),
            rate,
            utilities,
            rental,
            total_hours,
            net_amount
        ))

        payroll_id = cur.lastrowid

        for d, h in days:
            cur.execute("""
                INSERT INTO payroll_days (payroll_id, work_date, hours)
                VALUES (?, ?, ?)
            """, (payroll_id, d, h))

        self.conn.commit()
        return payroll_id

    # ================= PAYROLL HISTORY =================

    def get_payrolls(self):
        return self.conn.execute("""
            SELECT p.id,
                   e.name,
                   p.period_from,
                   p.period_to,
                   p.created_at,
                   p.net_amount
            FROM payrolls p
            JOIN employees e ON e.id = p.employee_id
            ORDER BY p.id DESC
        """).fetchall()

    def get_payroll_full(self, payroll_id):
        payroll = self.conn.execute("""
            SELECT p.*, e.name, e.rate AS employee_rate,
                   e.bank, e.iban, e.bic
            FROM payrolls p
            JOIN employees e ON e.id = p.employee_id
            WHERE p.id = ?
        """, (payroll_id,)).fetchone()

        days = self.conn.execute("""
            SELECT work_date, hours
            FROM payroll_days
            WHERE payroll_id = ?
            ORDER BY work_date
        """, (payroll_id,)).fetchall()

        return payroll, days

