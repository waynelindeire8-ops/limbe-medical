from main import HospitalManagementSystem
from models import Patient

def test_edit():
    hms = HospitalManagementSystem()
    
    # Cleanup existing test data
    hms.delete_patient("EDIT-TEST-1")
    hms.delete_patient("EDIT-TEST-2")
    
    # Add a test patient
    pid = "EDIT-TEST-1"
    p = Patient(patient_id=pid, first_name="Original", last_name="Patient")
    hms.add_patient(p)
    
    print(f"Original patient: {hms.get_patient(pid)}")
    
    # Update without ID change
    success = hms.update_patient(pid, first_name="Updated", last_name="Name")
    print(f"Update success (no ID change): {success}")
    updated_p = hms.get_patient(pid)
    print(f"Updated patient: {updated_p}")
    
    if updated_p.first_name != "Updated":
        print("FAILED: first_name not updated")
    
    # Update with ID change
    new_pid = "EDIT-TEST-2"
    # We pass patient_id as a keyword argument in the dict
    update_data = {
        'patient_id': new_pid,
        'first_name': "Changed ID"
    }
    success = hms.update_patient(pid, **update_data)
    print(f"Update success (ID change): {success}")
    
    old_p = hms.get_patient(pid)
    new_p = hms.get_patient(new_pid)
    
    print(f"Old ID patient (should be None): {old_p}")
    print(f"New ID patient: {new_p}")
    
    if old_p is not None:
        print("FAILED: old record still exists")
    if new_p is None:
        print("FAILED: new record not created")
    elif new_p.first_name != "Changed ID":
        print("FAILED: new record has wrong name")

if __name__ == "__main__":
    test_edit()
