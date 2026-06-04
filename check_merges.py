
import sqlite3
from collections import defaultdict

def check_merged_names():
    conn = sqlite3.connect('hospital_data.db')
    cursor = conn.cursor()
    
    # We can't see deleted records directly if they were hard-deleted,
    # but we can look at common names currently in the DB.
    cursor.execute("SELECT first_name, last_name, COUNT(*) FROM patients GROUP BY first_name, last_name HAVING COUNT(*) > 1")
    duplicates = cursor.fetchall()
    
    if duplicates:
        print("Current duplicates in DB:")
        for f, l, c in duplicates:
            print(f" - {f} {l}: {c} records")
    else:
        print("No exact name duplicates currently in DB.")

    # Let's check the logs for what happened during the merge
    cursor.execute("SELECT details FROM system_logs WHERE action LIKE '%merge%' OR action LIKE '%delete%' ORDER BY timestamp DESC LIMIT 100")
    logs = cursor.fetchall()
    print("\nRecent merge/delete logs:")
    for l in logs[:10]:
        print(f" - {l[0]}")

    conn.close()

if __name__ == "__main__":
    check_merged_names()
