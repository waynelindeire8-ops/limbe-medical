
import sqlite3
import os

def check_all_tables():
    db_path = 'hospital_data.db'
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"Found {len(tables)} tables in database.")
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f" - {table}: {count} records")
        except Exception as e:
            print(f" - {table}: Error {e}")
            
    conn.close()

if __name__ == "__main__":
    check_all_tables()
