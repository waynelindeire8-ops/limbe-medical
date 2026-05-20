from main import HospitalManagementSystem
from models import Patient
import os

def test_add_patients():
    data_file = "test_hospital_data.json"
    if os.path.exists(data_file):
        os.remove(data_file)
        
    hms = HospitalManagementSystem(data_file=data_file)
    
    for i in range(1, 6):
        p = Patient(
            patient_id=f"P{i}",
            first_name=f"First{i}",
            last_name=f"Last{i}",
            created_date="2024-01-01"
        )
        hms.add_patient(p)
        print(f"Added patient {i}, total: {len(hms.patients)}")
        
    if len(hms.patients) == 5:
        print("Successfully added 5 patients.")
    else:
        print(f"Failed: Only {len(hms.patients)} patients found.")

    # Reload data
    hms2 = HospitalManagementSystem(data_file=data_file)
    print(f"Reloaded total patients: {len(hms2.patients)}")
    
    if os.path.exists(data_file):
        os.remove(data_file)

if __name__ == "__main__":
    test_add_patients()
