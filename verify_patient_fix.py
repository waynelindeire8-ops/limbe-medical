
from main import HospitalManagementSystem
from models import Patient, Appointment, MedicalRecord
import os

def verify_fix():
    test_db = "verify_patient_fix.json"
    if os.path.exists(test_db):
        os.remove(test_db)
        
    hms = HospitalManagementSystem(data_file=test_db)
    
    # 1. Create a patient
    p1 = Patient(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        date_of_birth="1990-01-01"
    )
    hms.add_patient(p1)
    
    # 2. Create related records
    a1 = Appointment(appointment_id="A1", patient_id="P1", doctor_id="D1", appointment_date="2024-01-01", status="Scheduled")
    hms.schedule_appointment(a1)
    
    m1 = MedicalRecord(record_id="M1", patient_id="P1", doctor_id="D1", date="2024-01-01", diagnosis="Flu")
    hms.add_medical_record(m1)
    
    # 2.5 Add a dummy file
    hms.patient_files["P1"] = [{
        "file_name": "test.txt",
        "path": f"attachments{os.sep}P1{os.sep}test.txt",
        "uploaded_at": "2024-01-01 10:00:00"
    }]
    # Create dummy directory
    base_dir = os.path.dirname(os.path.abspath(hms.data_file))
    p1_dir = os.path.join(base_dir, 'attachments', 'P1')
    os.makedirs(p1_dir, exist_ok=True)
    with open(os.path.join(p1_dir, 'test.txt'), 'w') as f:
        f.write("test")
    
    print(f"Initial patient ID: {hms.get_patient('P1').patient_id}")
    print(f"Initial appointment patient ID: {hms.get_appointment('A1').patient_id}")
    print(f"Initial medical record patient ID: {hms.get_medical_record('M1').patient_id}")
    print(f"Initial file path: {hms.patient_files['P1'][0]['path']}")
    
    # 3. Update patient ID and other fields
    success = hms.update_patient("P1", patient_id="P2", first_name="Johnny", blood_group="O+")
    
    print(f"\nUpdate success: {success}")
    
    p2 = hms.get_patient("P2")
    if p2:
        print(f"Updated patient name: {p2.first_name}")
        print(f"Updated patient blood group: {p2.blood_group}")
        
        # 4. Verify related records were updated
        a1_updated = hms.get_appointment("A1")
        m1_updated = hms.get_medical_record("M1")
        
        print(f"Updated appointment patient ID: {a1_updated.patient_id}")
        print(f"Updated medical record patient ID: {m1_updated.patient_id}")
        
        # Verify file path and directory
        p2_file_path = hms.patient_files["P2"][0]["path"]
        print(f"Updated file path: {p2_file_path}")
        p2_dir = os.path.join(base_dir, 'attachments', 'P2')
        dir_exists = os.path.exists(p2_dir)
        print(f"Updated directory exists: {dir_exists}")
        
        if a1_updated.patient_id == "P2" and m1_updated.patient_id == "P2" and "P2" in p2_file_path and dir_exists:
            print("\nSUCCESS: Related records and files updated correctly.")
        else:
            print("\nFAILURE: Related records or files NOT updated correctly.")
    else:
        print("\nFAILURE: Patient not found by new ID.")
        
    # 5. Test uniqueness check
    p_other = Patient(patient_id="P_OTHER", first_name="Other", last_name="User")
    hms.add_patient(p_other)
    
    success_dup = hms.update_patient("P2", patient_id="P_OTHER")
    print(f"\nUpdate with duplicate ID success: {success_dup} (should be False)")
    
    if os.path.exists(test_db):
        os.remove(test_db)

if __name__ == "__main__":
    verify_fix()
