import sqlite3
import os

db_path = "hospital_data.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM patients")
    count = cursor.fetchone()[0]
    print(f"Current patients in DB: {count}")
    
    # Also check if they are sample names
    cursor.execute("SELECT first_name, last_name FROM patients LIMIT 5")
    rows = cursor.fetchall()
    print("Sample patients in DB:")
    for row in rows:
        print(f"  {row[0]} {row[1]}")
    conn.close()
else:
    print("Database not found")
