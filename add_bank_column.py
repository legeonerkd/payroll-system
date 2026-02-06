import sqlite3
import os

db_path = os.path.join(
    os.getenv("LOCALAPPDATA"),
    "PayrollSystem",
    "payroll.db"
)

print("DB path:", db_path)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("ALTER TABLE employees ADD COLUMN bank TEXT")

conn.commit()
conn.close()

print("✅ Column 'bank' added successfully")
