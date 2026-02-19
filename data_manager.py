"""
Data Manager - Compatibility layer for Hospital Management System GUI
This module provides the interface expected by the GUI components
"""

from main import HospitalManagementSystem, Patient, Doctor, Appointment, MedicalRecord, Bill, InventoryItem
from typing import List, Optional

class DataManager:
    """Data Manager class that wraps HospitalManagementSystem for GUI compatibility"""
    
    def __init__(self):
        self.hms = HospitalManagementSystem()
    
    # ID Generation
    def generate_id(self, prefix: str) -> str:
        """Generate unique ID with prefix"""
        return self.hms.generate_id(prefix)
    
    # Patient Management
    def get_all_patients(self) -> List[Patient]:
        """Get all patients"""
        return self.hms.patients
    
    def get_patient(self, patient_id: str) -> Optional[Patient]:
        """Get patient by ID"""
        return self.hms.get_patient(patient_id)
    
    def add_patient(self, patient: Patient) -> bool:
        """Add a new patient"""
        return self.hms.add_patient(patient)
    
    def update_patient(self, patient_id: str, **kwargs) -> bool:
        """Update patient information"""
        return self.hms.update_patient(patient_id, **kwargs)
    
    def search_patients(self, search_term: str) -> List[Patient]:
        """Search patients by name or ID"""
        return self.hms.search_patients(search_term)
    
    # Doctor Management
    def get_all_doctors(self) -> List[Doctor]:
        """Get all doctors"""
        return self.hms.doctors
    
    def get_doctor(self, doctor_id: str) -> Optional[Doctor]:
        """Get doctor by ID"""
        return self.hms.get_doctor(doctor_id)
    
    def add_doctor(self, doctor: Doctor) -> bool:
        """Add a new doctor"""
        return self.hms.add_doctor(doctor)
    
    def get_available_doctors(self) -> List[Doctor]:
        """Get all available doctors"""
        return self.hms.get_available_doctors()
    
    # Appointment Management
    def get_all_appointments(self) -> List[Appointment]:
        """Get all appointments"""
        return self.hms.appointments
    
    def get_appointment(self, appointment_id: str) -> Optional[Appointment]:
        """Get appointment by ID"""
        for appointment in self.hms.appointments:
            if appointment.appointment_id == appointment_id:
                return appointment
        return None
    
    def schedule_appointment(self, appointment: Appointment) -> bool:
        """Schedule a new appointment"""
        return self.hms.schedule_appointment(appointment)
    
    def update_appointment_status(self, appointment_id: str, status: str) -> bool:
        """Update appointment status"""
        return self.hms.update_appointment_status(appointment_id, status)
    
    def get_patient_appointments(self, patient_id: str) -> List[Appointment]:
        """Get all appointments for a patient"""
        return self.hms.get_patient_appointments(patient_id)
    
    def get_doctor_appointments(self, doctor_id: str, date: str) -> List[Appointment]:
        """Get doctor's appointments for a specific date"""
        return self.hms.get_doctor_appointments(doctor_id, date)
    
    # Medical Records Management
    def get_all_medical_records(self) -> List[MedicalRecord]:
        """Get all medical records"""
        return self.hms.medical_records
    
    def get_medical_record(self, record_id: str) -> Optional[MedicalRecord]:
        """Get medical record by ID"""
        for record in self.hms.medical_records:
            if record.record_id == record_id:
                return record
        return None
    
    def add_medical_record(self, record: MedicalRecord) -> bool:
        """Add a new medical record"""
        return self.hms.add_medical_record(record)
    
    def update_medical_record(self, record: MedicalRecord) -> bool:
        """Update medical record"""
        for i, existing_record in enumerate(self.hms.medical_records):
            if existing_record.record_id == record.record_id:
                self.hms.medical_records[i] = record
                self.hms.save_data()
                return True
        return False
    
    def delete_medical_record(self, record_id: str) -> bool:
        """Delete medical record"""
        for i, record in enumerate(self.hms.medical_records):
            if record.record_id == record_id:
                del self.hms.medical_records[i]
                self.hms.save_data()
                return True
        return False
    
    def get_patient_medical_records(self, patient_id: str) -> List[MedicalRecord]:
        """Get all medical records for a patient"""
        return self.hms.get_patient_medical_records(patient_id)
    
    # Billing Management
    def get_all_bills(self) -> List[Bill]:
        """Get all bills"""
        return self.hms.bills
    
    def get_bill(self, bill_id: str) -> Optional[Bill]:
        """Get bill by ID"""
        for bill in self.hms.bills:
            if bill.bill_id == bill_id:
                return bill
        return None
    
    def add_bill(self, bill: Bill) -> bool:
        """Create a new bill"""
        return self.hms.create_bill(bill)
    
    def update_bill(self, bill: Bill) -> bool:
        """Update bill"""
        for i, existing_bill in enumerate(self.hms.bills):
            if existing_bill.bill_id == bill.bill_id:
                self.hms.bills[i] = bill
                self.hms.save_data()
                return True
        return False
    
    def delete_bill(self, bill_id: str) -> bool:
        """Delete bill"""
        for i, bill in enumerate(self.hms.bills):
            if bill.bill_id == bill_id:
                del self.hms.bills[i]
                self.hms.save_data()
                return True
        return False
    
    def update_bill_status(self, bill_id: str, status: str) -> bool:
        """Update bill status"""
        return self.hms.update_bill_status(bill_id, status)
    
    def get_patient_bills(self, patient_id: str) -> List[Bill]:
        """Get all bills for a patient"""
        return self.hms.get_patient_bills(patient_id)
    
    # Inventory Management
    def get_all_inventory(self) -> List[InventoryItem]:
        """Get all inventory items"""
        return self.hms.inventory
    
    def get_inventory_item(self, item_id: str) -> Optional[InventoryItem]:
        """Get inventory item by ID"""
        for item in self.hms.inventory:
            if item.item_id == item_id:
                return item
        return None
    
    def add_inventory_item(self, item: InventoryItem) -> bool:
        """Add new inventory item"""
        return self.hms.add_inventory_item(item)
    
    def update_inventory_item(self, item: InventoryItem) -> bool:
        """Update inventory item"""
        for i, existing_item in enumerate(self.hms.inventory):
            if existing_item.item_id == item.item_id:
                self.hms.inventory[i] = item
                self.hms.save_data()
                return True
        return False
    
    def delete_inventory_item(self, item_id: str) -> bool:
        """Delete inventory item"""
        for i, item in enumerate(self.hms.inventory):
            if item.item_id == item_id:
                del self.hms.inventory[i]
                self.hms.save_data()
                return True
        return False
    
    def get_low_stock_items(self) -> List[InventoryItem]:
        """Get items with low stock"""
        return self.hms.get_low_stock_items()
    
    def update_inventory_quantity(self, item_id: str, quantity: int) -> bool:
        """Update inventory quantity"""
        return self.hms.update_inventory_quantity(item_id, quantity)

# Create a global instance for easy access
data_manager = DataManager()