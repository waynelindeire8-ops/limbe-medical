import sqlite3
import os

conn = sqlite3.connect('hospital_data.db')
cursor = conn.cursor()

print("Searching for '2026-05-20' in all tables...")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]

for table in tables:
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    for col in columns:
        try:
            cursor.execute(f"SELECT * FROM {table} WHERE \"{col}\" LIKE ?", ("%2026-05-20%",))
            results = cursor.fetchall()
            if results:
                print(f"Matches in table '{table}', column '{col}':")
                for r in results:
                    print(f" - {r}")
        except:
            pass
conn.close()
