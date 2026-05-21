import json
import sqlite3
import os
import sys

# Add current directory to path to import models
sys.path.append(os.getcwd())
from models import Doctor

def add_dept_and_doctor():
    db_path = "hospital_data.db"
    json_path = r"c:\Users\user\OneDrive\Limbe Medical\hospital_data.json"
    
    dept_name = "general one"
    doctor_id = "D-WENDY"
    doctor_data = {
        "doctor_id": doctor_id,
        "first_name": "Wendy",
        "last_name": "Ngwira",
        "specialty": dept_name,
        "phone": "0999808980",
        "email": "limbemedical@outlook.com",
        "status": "Available"
    }

    # 1. Update Database
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if doctor already exists
        cursor.execute("SELECT COUNT(*) FROM doctors WHERE doctor_id = ?", (doctor_id,))
        if cursor.fetchone()[0] == 0:
            # Create doctor object
            new_doctor = Doctor(**doctor_data)
            
            # Prepare fields for insertion
            from dataclasses import fields
            doc_fields = {f.name for f in fields(Doctor)}
            filtered = {k: v for k, v in doctor_data.items() if k in doc_fields}
            for f in fields(Doctor):
                if f.name not in filtered: filtered[f.name] = ""
                
            cols = ', '.join(filtered.keys())
            placeholders = ', '.join(['?'] * len(filtered))
            cursor.execute(f"INSERT INTO doctors ({cols}) VALUES ({placeholders})", list(filtered.values()))
            conn.commit()
            print(f"Added Dr. Wendy Ngwira to database in department '{dept_name}'.")
        else:
            print("Dr. Wendy Ngwira already exists in database.")
        
        # VERIFY
        cursor.execute("SELECT * FROM doctors WHERE last_name = 'Ngwira'")
        print(f"Verification from DB: {cursor.fetchone()}")
        conn.close()
    else:
        print("Database not found.")

    # 2. Update JSON
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Add department
            if 'departments' not in data:
                data['departments'] = []
            if dept_name not in data['departments']:
                data['departments'].append(dept_name)
                print(f"Added '{dept_name}' to departments in JSON.")
            
            # Add doctor
            if 'doctors' not in data:
                data['doctors'] = []
            
            # Check if doctor exists in JSON
            doc_exists = any(d.get('doctor_id') == doctor_id for d in data['doctors'])
            if not doc_exists:
                data['doctors'].append(doctor_data)
                print("Added Dr. Wendy Ngwira to doctors in JSON.")
            
            # Save updated JSON
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            print("JSON updated successfully.")
            
        except Exception as e:
            print(f"Error updating JSON: {e}")
    else:
        print("JSON file not found.")

if __name__ == "__main__":
    add_dept_and_doctor()
