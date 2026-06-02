import sqlite3

def find_id_in_all_tables(target_id):
    conn = sqlite3.connect('hospital_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    matches = []
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        cols = [row[1] for row in cursor.fetchall()]
        for col in cols:
            try:
                cursor.execute(f"SELECT * FROM {table} WHERE \"{col}\" = ?", (target_id,))
                rows = cursor.fetchall()
                if rows:
                    matches.append((table, col, rows))
            except:
                pass
    conn.close()
    return matches

target = "180163876"
print(f"Searching for {target}...")
for table, col, rows in find_id_in_all_tables(target):
    print(f"  Found in {table}.{col}:")
    for r in rows:
        print(f"    {r}")
