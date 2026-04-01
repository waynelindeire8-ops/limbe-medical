
from models import Patient
from typing import List

class MockHMS:
    def __init__(self):
        self.patients = []

    def search_patients(self, search_term: str) -> List[Patient]:
        search_term = search_term.lower()
        # The current implementation in main.py
        return [
            p for p in self.patients
            if search_term in p.first_name.lower()
            or search_term in p.last_name.lower()
            or search_term in (p.first_name.lower() + " " + p.last_name.lower())
            or search_term in (p.last_name.lower() + " " + p.first_name.lower())
            or search_term in p.patient_id.lower()
        ]

def test_search():
    hms = MockHMS()
    
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
        "Doe John"
    ]
    
    for term in test_cases:
        results = hms.search_patients(term)
        print(f"Search '{term}': {len(results)} found")

if __name__ == "__main__":
    test_search()
