import json
import sqlite3
import os
import sys
from dataclasses import fields

# Add current directory to path to import models
sys.path.append(os.getcwd())
from models import Appointment

def migrate():
    json_path = r"c:\Users\user\OneDrive\Limbe Medical\hospital_data.json"
    db_path = "hospital_data.db"
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    actual_appts = data.get('appointments', [])
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM appointments")
    print(f"Deleted existing appointments.")
    
    appt_fields = {f.name for f in fields(Appointment)}
    
    for a in actual_appts:
        if 'date' in a: a['appointment_date'] = a.pop('date')
        if 'time' in a: a['appointment_time'] = a.pop('time')
        
        filtered = {k: v for k, v in a.items() if k in appt_fields}
        for f in fields(Appointment):
            if f.name not in filtered: filtered[f.name] = ""
            
        cols = ', '.join(filtered.keys())
        placeholders = ', '.join(['?'] * len(filtered))
        cursor.execute(f"INSERT OR REPLACE INTO appointments ({cols}) VALUES ({placeholders})", list(filtered.values()))
    
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM appointments")
    count = cursor.fetchone()[0]
    conn.close()
    
    print(f"Migration complete. Total appointments in DB: {count}")

if __name__ == "__main__":
    migrate()
