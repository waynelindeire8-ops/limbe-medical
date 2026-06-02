import sqlite3

conn = sqlite3.connect('hospital_data.db')
cursor = conn.cursor()
cursor.execute('SELECT patient_id, first_name, last_name FROM patients WHERE first_name = "Unknown"')
results = cursor.fetchall()
print(f"Unknown patients: {len(results)}")
for r in results:
    print(f" - {r}")
conn.close()
