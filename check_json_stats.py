import json
import os

path = r"c:\Users\user\OneDrive\Limbe Medical\hospital_data.json"
if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    patients = data.get('patients', [])
    appointments = data.get('appointments', [])
    medical_records = data.get('medical_records', [])
    
    print(f"JSON Stats:")
    print(f"  Patients: {len(patients)}")
    print(f"  Appointments: {len(appointments)}")
    print(f"  Medical Records: {len(medical_records)}")
    
    # Check for duplicates or missing IDs in patients
    patient_ids = [p.get('patient_id') for p in patients]
    unique_ids = set(patient_ids)
    print(f"  Unique Patient IDs: {len(unique_ids)}")
    
    if len(patient_ids) != len(unique_ids):
        print(f"  Found {len(patient_ids) - len(unique_ids)} duplicate IDs")
else:
    print("File not found")
