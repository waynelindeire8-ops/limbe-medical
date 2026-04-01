
from main import HospitalManagementSystem
from models import Patient, Doctor, Appointment

def test_search():
    hms = HospitalManagementSystem()
    
    # Mock data if needed, but let's see what's in there
    print(f"Total patients: {len(hms.patients)}")
    if not hms.patients:
        hms.patients.append(Patient(patient_id="P1", first_name="John", last_name="Doe"))
        hms.patients.append(Patient(patient_id="P2", first_name="Jane", last_name="Smith"))
    
    # Test full name search
    results = hms.search_patients("John Doe")
    print(f"Search 'John Doe': {[p.patient_id for p in results]}")
    assert any(p.first_name == "John" and p.last_name == "Doe" for p in results)
    
    results = hms.search_patients("Doe John")
    print(f"Search 'Doe John': {[p.patient_id for p in results]}")
    assert any(p.first_name == "John" and p.last_name == "Doe" for p in results)
    
    # Test partial name search
    results = hms.search_patients("John")
    print(f"Search 'John': {[p.patient_id for p in results]}")
    assert any(p.first_name == "John" for p in results)
    
    # Test doctor search
    if not hms.doctors:
        hms.doctors.append(Doctor(doctor_id="D1", first_name="Gregory", last_name="House"))
        
    results = hms.search_doctors("Gregory House")
    print(f"Search 'Gregory House': {[d.doctor_id for d in results]}")
    assert any(d.first_name == "Gregory" and d.last_name == "House" for d in results)
    
    # Test appointment search
    if not hms.appointments:
        hms.appointments.append(Appointment(appointment_id="A1", patient_id="P1", doctor_id="D1", appointment_date="2024-01-01", status="Scheduled"))
        
    results = hms.search_appointments("John Doe")
    print(f"Search appointments for 'John Doe': {[a.appointment_id for a in results]}")
    assert any(a.appointment_id == "A1" for a in results)

if __name__ == "__main__":
    test_search()
