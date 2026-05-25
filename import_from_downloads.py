import json
import os
import sys
from main import HospitalManagementSystem
from models import Patient

def main():
    json_path = r"C:\Users\user\Downloads\hospital_data.json"
    
    if not os.path.exists(json_path):
        print(f"Error: File not found at {json_path}")
        return

    print(f"Reading data from {json_path}...")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return

    patients = data.get('patients', [])
    if not patients:
        print("No patients found in the JSON file.")
        return

    print(f"Found {len(patients)} patients. Starting import...")
    
    hms = HospitalManagementSystem()
    added = 0
    updated = 0
    errors = 0

    for p_data in patients:
        try:
            # Create Patient object. Filter out fields that don't belong to the model if necessary.
            # But the Patient dataclass in models.py seems to match the JSON structure.
            patient = Patient(**p_data)
            
            # Check if patient exists to provide better summary
            existing = hms.get_patient(patient.patient_id)
            
            if hms.add_patient(patient):
                if existing:
                    updated += 1
                else:
                    added += 1
            else:
                print(f"Failed to add patient {patient.patient_id}")
                errors += 1
        except Exception as e:
            print(f"Error processing patient data: {e}")
            errors += 1

    print("\nImport Summary:")
    print(f"Total processed: {len(patients)}")
    print(f"New patients added: {added}")
    print(f"Existing patients updated: {updated}")
    print(f"Errors: {errors}")
    print(f"Current total patients in system: {hms.get_patients_count()}")

if __name__ == "__main__":
    main()
