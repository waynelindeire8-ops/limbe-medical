
import json
import os
import sqlite3

def debug_ids():
    json_path = r"C:\Users\user\Downloads\hospital_data.json"
    db_path = "hospital_data.db"
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    json_ids = [str(p.get('patient_id')) for p in data.get('patients', [])]
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id FROM patients")
    db_ids = [str(row[0]) for row in cursor.fetchall()]
    conn.close()
    
    print(f"Sample JSON IDs: {json_ids[:5]}")
    print(f"Sample DB IDs: {db_ids[:5]}")
    
    missing = [jid for jid in json_ids if jid not in db_ids]
    print(f"Missing count: {len(missing)}")
    if missing:
        print(f"First 5 missing: {missing[:5]}")

if __name__ == "__main__":
    debug_ids()
