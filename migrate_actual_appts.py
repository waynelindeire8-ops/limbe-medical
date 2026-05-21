import json
import sqlite3
import os
import sys
from dataclasses import fields

# Add current directory to path to import models
sys.path.append(os.getcwd())
from models import Appointment

def migrate_appointments_only():
    json_path = r"c:\Users\user\OneDrive\Limbe Medical\hospital_data.json"
    db_path = os.path.join(os.getcwd(), "hospital_data.db")
    
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found")
        return

    print(f"Loading actual appointments from {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    actual_appointments = data.get('appointments', [])
    print(f"Found {len(actual_appointments)} actual appointments.")

    print(f"Opening database at {os.path.abspath(db_path)}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Clearing existing appointments...")
    cursor.execute("DELETE FROM appointments")
    rows_deleted = cursor.rowcount
    print(f"Deleted {rows_deleted} rows.")
    
    print("Migrating actual appointments...")
    appt_fields = {f.name for f in fields(Appointment)}
    
    count = 0
    for a_dict in actual_appointments:
        # Normalize fields if needed
        if 'date' in a_dict and 'appointment_date' not in a_dict:
            a_dict['appointment_date'] = a_dict.pop('date')
        if 'time' in a_dict and 'appointment_time' not in a_dict:
            a_dict['appointment_time'] = a_dict.pop('time')
            
        filtered = {k: v for k, v in a_dict.items() if k in appt_fields}
        for f in fields(Appointment):
            if f.name not in filtered: filtered[f.name] = ""
            
        cols = ', '.join(filtered.keys())
        placeholders = ', '.join(['?'] * len(filtered))
        cursor.execute(f"INSERT INTO appointments ({cols}) VALUES ({placeholders})", list(filtered.values()))
        count += 1

    conn.commit()
    conn.close()
    print(f"Successfully migrated {count} appointments.")

if __name__ == "__main__":
    migrate_appointments_only()
