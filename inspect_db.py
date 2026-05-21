import sqlite3
import os

db_path = "hospital_data.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM patients")
        count = cursor.fetchone()[0]
        print(f"Total patients in DB: {count}")
        
        cursor.execute("SELECT patient_id, first_name, last_name FROM patients LIMIT 10")
        rows = cursor.fetchall()
        print("First 10 patients in DB:")
        for row in rows:
            print(f"  ID: {row[0]}, Name: {row[1]} {row[2]}")
    except Exception as e:
        print(f"Error querying DB: {e}")
    finally:
        conn.close()
else:
    print("Database file 'hospital_data.db' not found in current directory.")
