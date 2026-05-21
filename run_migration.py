import json
import sqlite3
import os
from dataclasses import asdict
import sys

# Add current directory to path to import models
sys.path.append(os.getcwd())
from models import Patient

def migrate():
    json_path = r"c:\Users\user\OneDrive\Limbe Medical\hospital_data.json"
    db_path = "hospital_data.db"
    
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found")
        return

    print(f"Loading data from {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    patients_data = data.get('patients', [])
    print(f"Found {len(patients_data)} patients in JSON.")

    if not patients_data:
        print("No patients to migrate.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Clear existing patients if they are sample data
    # (Checking for 'Patient0' as a proxy for sample data)
    cursor.execute("SELECT COUNT(*) FROM patients WHERE first_name LIKE 'Patient%'")
    sample_count = cursor.fetchone()[0]
    if sample_count > 0:
        print(f"Removing {sample_count} sample patients...")
        cursor.execute("DELETE FROM patients")
        conn.commit()

    print("Migrating patients...")
    count = 0
    for p_dict in patients_data:
        # Filter fields to match Patient dataclass
        import dataclasses
        allowed_fields = {f.name for f in dataclasses.fields(Patient)}
        filtered_data = {k: v for k, v in p_dict.items() if k in allowed_fields}
        
        # Ensure all required fields are present with defaults
        for field in dataclasses.fields(Patient):
            if field.name not in filtered_data:
                filtered_data[field.name] = ""
        
        cols = ', '.join(filtered_data.keys())
        placeholders = ', '.join(['?'] * len(filtered_data))
        sql = f"INSERT OR REPLACE INTO patients ({cols}) VALUES ({placeholders})"
        cursor.execute(sql, list(filtered_data.values()))
        count += 1
        if count % 1000 == 0:
            print(f"  Migrated {count} patients...")

    conn.commit()
    conn.close()
    print(f"Successfully migrated {count} patients to {db_path}.")

if __name__ == "__main__":
    migrate()
