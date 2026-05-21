import json
import sqlite3
import os
import sys

def cleanup():
    db_path = "hospital_data.db"
    json_path = r"c:\Users\user\OneDrive\Limbe Medical\hospital_data.json"
    
    # 1. Update Database
    print(f"Opening database at {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check doctors in General department
    cursor.execute("SELECT COUNT(*) FROM doctors WHERE specialty = 'General'")
    count = cursor.fetchone()[0]
    print(f"Found {count} doctors in General department.")
    
    if count > 0:
        print("Deleting doctors in General department...")
        cursor.execute("DELETE FROM doctors WHERE specialty = 'General'")
        print(f"Deleted {cursor.rowcount} doctors.")
    
    conn.commit()
    conn.close()
    
    # 2. Update JSON Metadata
    if os.path.exists(json_path):
        print(f"Updating JSON metadata in {json_path}...")
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'departments' in data:
            if 'General' in data['departments']:
                data['departments'].remove('General')
                print("Removed 'General' from departments list.")
            
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    print("Cleanup complete.")

if __name__ == "__main__":
    cleanup()
