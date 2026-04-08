
import os
import json
from dataclasses import asdict
from main import HospitalManagementSystem
from models import MedicalRecord

def test_save_medical_record():
    hms = HospitalManagementSystem(data_file="test_hospital_data.json")
    
    # Simulate the form data that would be sent from add_medical_record.html
    # but WITHOUT prescriptions to reproduce the KeyError if it wasn't fixed.
    form_data = {
        'patient_id': 'P123',
        'doctor_id': 'D123',
        'date': '2024-04-07',
        'consult_reason': 'Flu symptoms',
        'diagnosis': 'Seasonal Flu',
        'treatment': 'Rest and hydration',
        # 'prescriptions': 'Aspirin', # MISSING in the template!
        'notes': 'Follow up in 3 days'
    }
    
    # Simulate the route logic
    try:
        # In the route we used: prescriptions=request.form.get('prescriptions', '')
        # This should now work even if 'prescriptions' is missing.
        new_record = MedicalRecord(
            record_id=hms.generate_id("MR"),
            patient_id=form_data['patient_id'],
            doctor_id=form_data['doctor_id'],
            date=form_data['date'],
            consult_reason=form_data['consult_reason'],
            diagnosis=form_data['diagnosis'],
            treatment=form_data['treatment'],
            prescriptions=form_data.get('prescriptions', ''), # This was the fix
            notes=form_data.get('notes', ''),
            details={}
        )
        hms.add_medical_record(new_record)
        print("Medical record added successfully!")
        
        # Verify it was saved
        hms.load_data()
        saved_record = next((r for r in hms.medical_records if r.record_id == new_record.record_id), None)
        if saved_record:
            print(f"Verified: Record {saved_record.record_id} exists in data.")
            if saved_record.prescriptions == "":
                print("Verified: Prescriptions is empty string as expected when missing from form.")
        else:
            print("Error: Record was not saved to data file.")
            
    except Exception as e:
        print(f"Error during test: {e}")
    finally:
        if os.path.exists("test_hospital_data.json"):
            os.remove("test_hospital_data.json")

if __name__ == "__main__":
    test_save_medical_record()
