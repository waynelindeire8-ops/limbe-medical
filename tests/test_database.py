"""
Test Suite for Database Operations
"""

import unittest
import os
import tempfile
from database.db_manager import DatabaseManager
from utils.helpers import IDGenerator, Validator, DateTimeHelper


class TestDatabaseManager(unittest.TestCase):
    """Test database manager operations"""
    
    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = DatabaseManager(self.temp_db.name, use_supabase=False)
    
    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.temp_db.name):
            os.remove(self.temp_db.name)
    
    def test_add_patient(self):
        """Test adding a patient"""
        patient = {
            'patient_id': IDGenerator.generate_patient_id(),
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'gender': 'Male',
            'phone': '1234567890',
            'email': 'john@example.com',
            'address': '123 Main St',
        }
        
        result = self.db.add_patient(patient)
        self.assertTrue(result)
        
        retrieved = self.db.get_patient(patient['patient_id'])
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['first_name'], 'John')
    
    def test_get_all_patients(self):
        """Test retrieving all patients"""
        patient1 = {
            'patient_id': IDGenerator.generate_patient_id(),
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'gender': 'Male',
            'phone': '1234567890',
            'email': 'john@example.com',
            'address': '123 Main St',
        }
        
        patient2 = {
            'patient_id': IDGenerator.generate_patient_id(),
            'first_name': 'Jane',
            'last_name': 'Smith',
            'date_of_birth': '1992-05-15',
            'gender': 'Female',
            'phone': '0987654321',
            'email': 'jane@example.com',
            'address': '456 Oak Ave',
        }
        
        self.db.add_patient(patient1)
        self.db.add_patient(patient2)
        
        patients = self.db.get_all_patients()
        self.assertEqual(len(patients), 2)
    
    def test_search_patients(self):
        """Test searching patients"""
        patient = {
            'patient_id': IDGenerator.generate_patient_id(),
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'gender': 'Male',
            'phone': '1234567890',
            'email': 'john@example.com',
            'address': '123 Main St',
        }
        
        self.db.add_patient(patient)
        
        results = self.db.search_patients('John')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['first_name'], 'John')
    
    def test_update_patient(self):
        """Test updating a patient"""
        patient = {
            'patient_id': IDGenerator.generate_patient_id(),
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'gender': 'Male',
            'phone': '1234567890',
            'email': 'john@example.com',
            'address': '123 Main St',
        }
        
        self.db.add_patient(patient)
        
        update_data = {'phone': '9999999999'}
        result = self.db.update_patient(patient['patient_id'], update_data)
        self.assertTrue(result)
        
        updated = self.db.get_patient(patient['patient_id'])
        self.assertEqual(updated['phone'], '9999999999')
    
    def test_delete_patient(self):
        """Test deleting a patient"""
        patient = {
            'patient_id': IDGenerator.generate_patient_id(),
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'gender': 'Male',
            'phone': '1234567890',
            'email': 'john@example.com',
            'address': '123 Main St',
        }
        
        self.db.add_patient(patient)
        result = self.db.delete_patient(patient['patient_id'])
        self.assertTrue(result)
        
        retrieved = self.db.get_patient(patient['patient_id'])
        self.assertIsNone(retrieved)
    
    def test_add_doctor(self):
        """Test adding a doctor"""
        doctor = {
            'doctor_id': IDGenerator.generate_doctor_id(),
            'first_name': 'Dr.',
            'last_name': 'Smith',
            'specialization': 'Cardiology',
            'license_number': 'LIC123456',
            'phone': '1234567890',
            'email': 'smith@hospital.com',
            'department': 'Cardiology',
        }
        
        result = self.db.add_doctor(doctor)
        self.assertTrue(result)
    
    def test_add_appointment(self):
        """Test adding an appointment"""
        appointment = {
            'appointment_id': IDGenerator.generate_appointment_id(),
            'patient_id': 'PAT-12345678',
            'doctor_id': 'DOC-12345678',
            'appointment_date': '2024-02-15',
            'appointment_time': '10:00',
            'status': 'scheduled',
        }
        
        result = self.db.add_appointment(appointment)
        self.assertTrue(result)
    
    def test_add_bill(self):
        """Test adding a bill"""
        bill = {
            'bill_id': IDGenerator.generate_bill_id(),
            'patient_id': 'PAT-12345678',
            'amount': 500.00,
            'status': 'pending',
        }
        
        result = self.db.add_bill(bill)
        self.assertTrue(result)
    
    def test_add_inventory_item(self):
        """Test adding inventory item"""
        item = {
            'item_id': IDGenerator.generate_item_id(),
            'item_name': 'Aspirin',
            'category': 'Medicine',
            'quantity': 100,
            'unit_price': 5.00,
            'reorder_level': 20,
        }
        
        result = self.db.add_inventory_item(item)
        self.assertTrue(result)
    
    def test_get_low_stock_items(self):
        """Test getting low stock items"""
        item = {
            'item_id': IDGenerator.generate_item_id(),
            'item_name': 'Bandages',
            'category': 'Supplies',
            'quantity': 5,
            'unit_price': 2.00,
            'reorder_level': 20,
        }
        
        self.db.add_inventory_item(item)
        
        low_stock = self.db.get_low_stock_items()
        self.assertGreater(len(low_stock), 0)


class TestValidators(unittest.TestCase):
    """Test validation functions"""
    
    def test_validate_email(self):
        """Test email validation"""
        self.assertTrue(Validator.validate_email('test@example.com'))
        self.assertFalse(Validator.validate_email('invalid-email'))
        self.assertFalse(Validator.validate_email('test@'))
    
    def test_validate_phone(self):
        """Test phone validation"""
        self.assertTrue(Validator.validate_phone('1234567890'))
        self.assertTrue(Validator.validate_phone('(123) 456-7890'))
        self.assertFalse(Validator.validate_phone('123'))
    
    def test_validate_date(self):
        """Test date validation"""
        self.assertTrue(Validator.validate_date('2024-02-15'))
        self.assertFalse(Validator.validate_date('2024-13-45'))
        self.assertFalse(Validator.validate_date('invalid-date'))
    
    def test_validate_password(self):
        """Test password validation"""
        self.assertTrue(Validator.validate_password('SecurePass123'))
        self.assertFalse(Validator.validate_password('weak'))
        self.assertFalse(Validator.validate_password('nouppercase123'))


class TestHelpers(unittest.TestCase):
    """Test helper functions"""
    
    def test_id_generation(self):
        """Test ID generation"""
        patient_id = IDGenerator.generate_patient_id()
        self.assertTrue(patient_id.startswith('PAT-'))
        
        doctor_id = IDGenerator.generate_doctor_id()
        self.assertTrue(doctor_id.startswith('DOC-'))
    
    def test_date_formatting(self):
        """Test date formatting"""
        date_str = '2024-02-15T10:30:00'
        formatted = DateTimeHelper.format_date(date_str, '%d/%m/%Y')
        self.assertEqual(formatted, '15/02/2024')
    
    def test_age_calculation(self):
        """Test age calculation"""
        age = DateTimeHelper.get_age('1990-01-01')
        self.assertGreater(age, 30)


if __name__ == '__main__':
    unittest.main()
