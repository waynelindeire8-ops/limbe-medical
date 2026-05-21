import sqlite3
import json
import os

def remove_general():
    db_path = "hospital_data.db"
    json_path = r"c:\Users\user\OneDrive\Limbe Medical\hospital_data.json"
    
    # 1. Database Cleanup
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check doctors with different casing
        cursor.execute("SELECT COUNT(*) FROM doctors WHERE UPPER(specialty) = 'GENERAL'")
        count = cursor.fetchone()[0]
        print(f"Found {count} doctors with specialty 'GENERAL' (case-insensitive) in DB.")
        
        if count > 0:
            cursor.execute("DELETE FROM doctors WHERE UPPER(specialty) = 'GENERAL'")
            conn.commit()
            print(f"Deleted {cursor.rowcount} doctors from DB.")
        
        conn.close()
    else:
        print("Database not found.")

    # 2. JSON Cleanup (Doctors list)
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Remove doctors from the 'doctors' list if they have General specialty
            if 'doctors' in data:
                original_count = len(data['doctors'])
                data['doctors'] = [d for d in data['doctors'] if d.get('specialty', '').upper() != 'GENERAL' and d.get('specialization', '').upper() != 'GENERAL']
                new_count = len(data['doctors'])
                if original_count != new_count:
                    print(f"Removed {original_count - new_count} doctors from JSON 'doctors' list.")
                else:
                    print("No doctors with 'GENERAL' specialty found in JSON 'doctors' list.")
            
            # Also check for 'departments' key just in case it was missed or added recently
            if 'departments' in data:
                if 'General' in data['departments']:
                    data['departments'].remove('General')
                    print("Removed 'General' from departments list in JSON.")
                if 'GENERAL' in data['departments']:
                    data['departments'].remove('GENERAL')
                    print("Removed 'GENERAL' from departments list in JSON.")

            # Try to save
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            print("JSON updated successfully.")
            
        except Exception as e:
            print(f"Error updating JSON: {e}")
    else:
        print("JSON file not found.")

if __name__ == "__main__":
    remove_general()
