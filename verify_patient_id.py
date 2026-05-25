from models import Patient

try:
    # This should fail because patient_id is now mandatory
    p = Patient()
    print("Test Failed: Patient created without ID")
except TypeError as e:
    print(f"Test Passed: {e}")

try:
    # This should work
    p = Patient(patient_id="TEST-001")
    print(f"Test Passed: Patient created with ID: {p.patient_id}")
except TypeError as e:
    print(f"Test Failed: {e}")
