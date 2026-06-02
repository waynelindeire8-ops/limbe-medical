
import os
import sqlite3

def find_databases():
    paths = [
        'hospital_data.db',
        r"C:\Users\user\OneDrive\Limbe Medical\hospital_data.db",
        r"C:\Users\user\Downloads\hospital_data.db"
    ]
    
    for path in paths:
        if os.path.exists(path):
            print(f"Found DB at: {path}")
            try:
                conn = sqlite3.connect(path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM patients")
                count = cursor.fetchone()[0]
                print(f" - Patients: {count}")
                conn.close()
            except Exception as e:
                print(f" - Error reading: {e}")
        else:
            print(f"Not found: {path}")

if __name__ == "__main__":
    find_databases()
