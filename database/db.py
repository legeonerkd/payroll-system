from config import DATABASE_PATH
import sqlite3


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_PATH)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()
        self._init_db()

    # ==================================================
    # INIT
    # ==================================================
    def _init_db(self):
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                rate REAL NOT NULL,
                bank TEXT,
                iban TEXT,
                bic TEXT
            )
        """)

        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS work_hours (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                work_date TEXT NOT NULL,
                hours REAL NOT NULL,
                UNIQUE(employee_id, work_date),
                FOREIGN KEY(employee_id) REFERENCES employees(id)
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

    def add_employee(self, name: str, rate: float, bank: str = None, iban: str = None, bic: str = None):
        self.cur.execute(
            "INSERT INTO employees (name, rate, bank, iban, bic) VALUES (?, ?, ?, ?, ?)",
            (name, rate, bank, iban, bic),
        )
        self.conn.commit()

    def update_employee(self, emp_id: int, name: str, rate: float, bank: str = None, iban: str = None, bic: str = None):
        self.cur.execute(
            "UPDATE employees SET name=?, rate=?, bank=?, iban=?, bic=? WHERE id=?",
            (name, rate, bank, iban, bic, emp_id),
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
    
    def save_hours_batch(self, emp_id: int, hours_dict: dict):
        """
        Сохранение нескольких записей часов за раз
        hours_dict: {"YYYY-MM-DD": hours, ...}
        """
        for date, hours in hours_dict.items():
            if hours > 0:  # Сохраняем только ненулевые значения
                self.save_hours(emp_id, date, hours)
    
    def get_all_hours(self):
        """Получить всю историю отработанных часов"""
        return self.cur.execute(
            """
            SELECT 
                e.name as employee_name,
                w.work_date,
                w.hours,
                e.rate
            FROM work_hours w
            JOIN employees e ON w.employee_id = e.id
            ORDER BY w.work_date DESC, e.name
            """
        ).fetchall()
    
    def export_hours_to_csv(self, filepath: str):
        """Экспорт всей истории часов в CSV файл"""
        import csv
        
        hours_data = self.get_all_hours()
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Employee', 'Date', 'Hours', 'Rate (€/h)', 'Amount (€)'])
            
            for row in hours_data:
                employee_name = row['employee_name']
                work_date = row['work_date']
                hours = row['hours']
                rate = row['rate']
                amount = hours * rate
                
                writer.writerow([employee_name, work_date, hours, f"{rate:.2f}", f"{amount:.2f}"])
        
        return filepath

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

