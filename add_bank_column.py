"""Compatibility entry point: perform the complete, backed-up migration."""
from database.db import Database

if __name__ == '__main__':
    db = Database()
    try:
        print('Database schema is current. Backup:', db.last_backup)
    finally:
        db.close()
