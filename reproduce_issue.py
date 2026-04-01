from main import HospitalManagementSystem
from models import Patient
import os

def test_search():
    # Use a temporary data file for testing
    test_db = "test_hospital_data.json"
    if os.path.exists(test_db):
        os.remove(test_db)
        
    hms = HospitalManagementSystem(data_file=test_db)
    
    # Add a sample patient
    patient = Patient(
        patient_id="P001",
        first_name="John",
        last_name="Doe",
        date_of_birth="1990-01-01",
        gender="Male",
        phone="1234567890",
        address="123 Main St",
        email="john.doe@example.com",
        blood_group="O+",
        medical_history="None"
    )
    hms.patients.append(patient)
    
    print(f"Added patient: {patient.first_name} {patient.last_name}")
    
    # Test search by first name
    results = hms.search_patients("John")
    print(f"Search 'John': {len(results)} found")
    
    # Test search by last name
    results = hms.search_patients("Doe")
    print(f"Search 'Doe': {len(results)} found")
    
    # Test search by full name
    results = hms.search_patients("John Doe")
    print(f"Search 'John Doe': {len(results)} found")
    
    # Test search by reversed full name
    results = hms.search_patients("Doe John")
    print(f"Search 'Doe John': {len(results)} found")

    if os.path.exists(test_db):
        os.remove(test_db)

if __name__ == "__main__":
    test_search()
