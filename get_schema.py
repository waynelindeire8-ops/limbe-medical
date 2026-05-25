import sqlite3
conn = sqlite3.connect('hospital_data.db')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(patients)")
columns = cursor.fetchall()
for col in columns:
    print(col)
conn.close()
