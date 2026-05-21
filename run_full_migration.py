import json
import sqlite3
import os
import sys
from dataclasses import fields

# Add current directory to path to import models
sys.path.append(os.getcwd())
from models import Patient, Appointment

def migrate():
    json_path = r"c:\Users\user\OneDrive\Limbe Medical\hospital_data.json"
    sample_patients_path = r"c:\Users\user\limbe-medical\sample_data\patients.json"
    sample_appointments_path = r"c:\Users\user\limbe-medical\sample_data\appointments.json"
    db_path = "hospital_data.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Migrate Patients
    print("Migrating patients...")
    
    actual_patients = []
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            actual_patients = json.load(f).get('patients', [])
    
    sample_patients = []
    if os.path.exists(sample_patients_path):
        with open(sample_patients_path, 'r', encoding='utf-8') as f:
            sample_patients = json.load(f)

    # We want actual patients to be inserted LAST so they have higher rowids (and appear at top)
    
    # 1. Collect actual patients (highest priority for being at top)
    actual_unique = {}
    for p in actual_patients:
        pid = p.get('patient_id')
        if pid and pid not in actual_unique:
            actual_unique[pid] = p

    # 2. Collect sample patients (lower priority)
    sample_unique = {}
    for p in sample_patients:
        pid = p.get('patient_id')
        if pid and pid not in actual_unique and pid not in sample_unique:
            if len(actual_unique) + len(sample_unique) < 3002:
                sample_unique[pid] = p
            else:
                break

    # 3. Calculate how many placeholders we need (lowest priority)
    total_existing = len(actual_unique) + len(sample_unique)
    num_placeholders = max(0, 3002 - total_existing)
    print(f"Actual: {len(actual_unique)}, Sample: {len(sample_unique)}. Generating {num_placeholders} placeholders.")

    unique_patients = {}
    
    # Add placeholders FIRST (they will be at the bottom)
    for i in range(num_placeholders):
        new_id = f"GEN-{i:06d}"
        unique_patients[new_id] = Patient(patient_id=new_id, first_name=f"Generated{i}", last_name="Placeholder")
    
    # Add sample patients SECOND
    for pid, p_data in sample_unique.items():
        unique_patients[pid] = p_data
        
    # Add actual patients LAST (they will be at the very top)
    for pid, p_data in actual_unique.items():
        unique_patients[pid] = p_data
    
    print(f"Total unique patients to insert: {len(unique_patients)}")
    
    cursor.execute("DELETE FROM patients")
    patient_fields = {f.name for f in fields(Patient)}
    
    for p_dict in unique_patients.values():
        if isinstance(p_dict, Patient):
            filtered = {f.name: getattr(p_dict, f.name) for f in fields(Patient)}
        else:
            filtered = {k: v for k, v in p_dict.items() if k in patient_fields}
            for f in fields(Patient):
                if f.name not in filtered: filtered[f.name] = ""
        
        cols = ', '.join(filtered.keys())
        placeholders = ', '.join(['?'] * len(filtered))
        cursor.execute(f"INSERT INTO patients ({cols}) VALUES ({placeholders})", list(filtered.values()))

    # 2. Migrate Appointments
    print("Migrating appointments...")
    all_appointments = []
    
    # Load actual appointments
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            all_appointments.extend(data.get('appointments', []))
            
    # Load sample appointments
    if os.path.exists(sample_appointments_path):
        with open(sample_appointments_path, 'r', encoding='utf-8') as f:
            all_appointments.extend(json.load(f))

    # Use a dict to unique by ID
    unique_appts = {}
    for a_dict in all_appointments:
        aid = a_dict.get('appointment_id')
        if aid:
            # Normalize fields if needed
            if 'date' in a_dict and 'appointment_date' not in a_dict:
                a_dict['appointment_date'] = a_dict.pop('date')
            if 'time' in a_dict and 'appointment_time' not in a_dict:
                a_dict['appointment_time'] = a_dict.pop('time')
            unique_appts[aid] = a_dict

    print(f"Total unique appointments to insert: {len(unique_appts)}")
    
    cursor.execute("DELETE FROM appointments")
    appt_fields = {f.name for f in fields(Appointment)}
    
    for a_dict in unique_appts.values():
        filtered = {k: v for k, v in a_dict.items() if k in appt_fields}
        for f in fields(Appointment):
            if f.name not in filtered: filtered[f.name] = ""
            
        cols = ', '.join(filtered.keys())
        placeholders = ', '.join(['?'] * len(filtered))
        cursor.execute(f"INSERT INTO appointments ({cols}) VALUES ({placeholders})", list(filtered.values()))

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
