"""
Models - Re-exports data models from the main Hospital Management System
"""

from dataclasses import dataclass, field

@dataclass
class Patient:
    patient_id: str
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    phone: str
    email: str
    address: str
    emergency_contact: str
    medical_history: str
    created_date: str
    scheme_provider: str = ""
    scheme_type: str = ""


@dataclass
class Doctor:
    doctor_id: str
    first_name: str
    last_name: str
    specialty: str
    phone: str
    email: str
    status: str
    schedule: str = ""


@dataclass
class Appointment:
    appointment_id: str
    patient_id: str
    doctor_id: str
    appointment_date: str
    appointment_time: str
    reason: str
    status: str
    notes: str


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
    prescription_id: str
    patient_id: str
    doctor_id: str
    date: str
    medication: str
    dosage: str
    frequency: str
    duration: str
    notes: str
    status: str


@dataclass
class Bill:
    bill_id: str
    patient_id: str
    appointment_id: str
    amount: float
    services: str
    status: str
    created_date: str


@dataclass
class InventoryItem:
    item_id: str
    name: str
    category: str
    quantity: int
    unit_price: float
    supplier: str
    expiry_date: str
    min_quantity: int
    dosage_form: str
    strength: str
    batch_number: str
    notes: str


@dataclass
class User:
    user_id: str = ""
    username: str = ""
    password_salt: str = ""
    password_hash: str = ""
    role: str = ""
    otp_secret: str = ""
    otp_enabled: bool = False
    is_verified: bool = False
    is_active: bool = False


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
    status: str = "Waiting"
    priority: str = "Normal"
    arrival_time: str = ""
    estimated_wait: str = ""
    department: str = ""
    visit_reason: str = ""
    special_category: str = ""
    check_in_time: str = ""
    assigned_doctor_id: str = ""
    called_time: str = ""
    consultation_start_time: str = ""
    consultation_end_time: str = ""
    no_show_time: str = ""



# Re-export all models for GUI compatibility
__all__ = ['Patient', 'Doctor', 'Appointment', 'MedicalRecord', 'Prescription', 'Bill', 'InventoryItem', 'User', 'Message', 'QueueItem']
