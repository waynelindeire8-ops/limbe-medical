
from main import HospitalManagementSystem
from models import Patient
from typing import List
import os

def test_search():
    # Mocking self.patients directly for the test
    class TestHMS(HospitalManagementSystem):
        def __init__(self):
            self.patients = []
            self.doctors = []
            self.appointments = []
            self.settings = {}

    hms = TestHMS()
    
    # Add a sample patient
    patient = Patient(
        patient_id="P001",
        first_name="John",
        last_name="Doe",
    )
    hms.patients.append(patient)
    
    print(f"Added patient: '{patient.first_name}' '{patient.last_name}'")
    
    # Test cases
    test_cases = [
        "John",
        "Doe",
        "John Doe",
        "john doe",
        "John Doe ",  # Trailing space
        " John Doe",  # Leading space
        "John  Doe",  # Double space
        "Doe John",   # Reversed
        "P001",       # ID
        "john p001"   # Part of name and ID
    ]
    
    success = True
    for term in test_cases:
        results = hms.search_patients(term)
        found = len(results) > 0
        print(f"Search '{term}': {'SUCCESS' if found else 'FAILED'}")
        if not found:
            success = False
            
    if success:
        print("\nALL SEARCH TESTS PASSED!")
    else:
        print("\nSOME SEARCH TESTS FAILED!")

if __name__ == "__main__":
    test_search()
