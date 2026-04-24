"""
Models - Re-exports data models from the main Hospital Management System
"""

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Patient:
    patient_id: str = ""
    first_name: str = ""
    last_name: str = ""
    date_of_birth: str = ""
    gender: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    emergency_contact: str = ""
    blood_group: str = ""
    medical_history: str = ""
    created_date: str = ""
    scheme_provider: str = ""
    scheme_type: str = ""


@dataclass
class Doctor:
    doctor_id: str = ""
    first_name: str = ""
    last_name: str = ""
    specialty: str = ""
    phone: str = ""
    email: str = ""
    schedule: str = ""
    status: str = ""


@dataclass
class Appointment:
    appointment_id: str = ""
    patient_id: str = ""
    doctor_id: str = ""
    appointment_date: str = ""
    appointment_time: str = ""
    reason: str = ""
    status: str = ""
    notes: str = ""


@dataclass
class MedicalRecord:
    record_id: str = ""
    patient_id: str = ""
    doctor_id: str = ""
    date: str = ""
    consult_reason: str = ""
    diagnosis: str = ""
    treatment: str = ""
    prescriptions: str = ""
    notes: str = ""
    # Grouped fields for flexibility and cleaner model
    details: dict = field(default_factory=dict)


@dataclass
class Prescription:
    prescription_id: str = ""
    patient_id: str = ""
    doctor_id: str = ""
    date: str = ""
    medication: str = ""
    duration: str = ""
    notes: str = ""
    status: str = ""


@dataclass
class Bill:
    bill_id: str = ""
    patient_id: str = ""
    appointment_id: str = ""
    amount: float = 0.0
    services: str = ""
    status: str = ""
    created_date: str = ""
    provider: str = ""
    items: list = field(default_factory=list)
    created_at: str = ""  # ISO format timestamp for sorting


@dataclass
class InventoryItem:
    item_id: str = ""
    name: str = ""
    category: str = ""
    quantity: int = 0
    unit_price: float = 0.0
    supplier: str = ""
    expiry_date: str = ""
    min_quantity: int = 0
    dosage_form: str = ""
    strength: str = ""
    batch_number: str = ""
    notes: str = ""
    is_medicine: bool = False
    billing_codes: dict = field(default_factory=dict)  # e.g. {"provider1": "code1", "provider2": "code2"}


@dataclass
class User:
    user_id: str = ""
    username: str = ""
    password_salt: str = ""
    password_hash: str = ""
    role: str = ""
    is_active: bool = True
    is_verified: bool = False
    otp_enabled: bool = False
    otp_secret: Optional[str] = None


@dataclass
class Message:
    message_id: str = ""
    sender_id: str = ""
    sender_name: str = ""
    recipient_id: str = ""
    subject: str = ""
    content: str = ""
    timestamp: str = ""
    is_read: bool = False
    is_archived: bool = False


@dataclass
class QueueItem:
    queue_id: str = ""
    patient_id: str = ""
    patient_name: str = ""
    doctor_id: str = ""
    status: str = "Waiting"  # Waiting, Calling, In Consultation, Completed, No-show, Re-queued
    priority: str = "Routine" # Emergency, Urgent, Routine
    arrival_time: str = ""
    estimated_wait: str = ""
    department: str = ""
    visit_reason: str = ""
    special_category: str = ""
    check_in_time: str = ""
    assigned_doctor_id: str = ""
    doctor_name: str = ""
    # Added details
    triage_level: str = "3" # 1 (Critical) to 5 (Non-urgent)
    date_added: str = ""  # New field for date added
    vitals: dict = field(default_factory=dict) # {bp: "120/80", temp: "36.5", weight: "70"}
    assigned_nurse_id: str = ""
    last_called_time: str = ""
    requeued_count: int = 0
    notes: str = ""


@dataclass
class LabResult:
    result_id: str = ""
    patient_id: str = ""
    doctor_id: str = ""
    test_name: str = ""
    test_date: str = ""
    result_value: str = ""
    units: str = ""
    reference_range: str = ""
    status: str = "Pending" # Pending, Completed, Cancelled
    notes: str = ""


# Re-export all models for GUI compatibility
__all__ = ['Patient', 'Doctor', 'Appointment', 'MedicalRecord', 'Prescription', 'Bill', 'InventoryItem', 'User', 'Message', 'QueueItem', 'LabResult']
