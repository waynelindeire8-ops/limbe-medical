"""
Data Models for Hospital Management System
Matches Limbe Medical project structure
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
from datetime import datetime


@dataclass
class Patient:
    """Patient model"""
    patient_id: str
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    phone: str
    email: str
    address: str
    emergency_contact: str = ""
    medical_history: str = ""
    allergies: str = ""
    current_medications: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Doctor:
    """Doctor model"""
    doctor_id: str
    first_name: str
    last_name: str
    specialization: str
    license_number: str
    phone: str
    email: str
    department: str
    availability: str = "Available"
    years_of_experience: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Appointment:
    """Appointment model"""
    appointment_id: str
    patient_id: str
    doctor_id: str
    appointment_date: str
    appointment_time: str
    status: str  # scheduled, completed, cancelled
    reason: str = ""
    notes: str = ""
    department: str = ""
    priority: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class MedicalRecord:
    """Medical record model"""
    record_id: str
    patient_id: str
    doctor_id: str
    visit_date: str = ""
    date: str = ""
    diagnosis: str = ""
    treatment: str = ""
    prescription: str = ""
    prescriptions: str = ""
    notes: str = ""
    consult_reason: str = ""
    vital_signs: str = ""  # JSON string with BP, HR, Temp, etc.
    details: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Prescription:
    """Prescription model"""
    prescription_id: str
    patient_id: str
    doctor_id: str
    medication_name: str
    dosage: str
    frequency: str
    duration: str
    instructions: str = ""
    issued_date: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Bill:
    """Bill model"""
    bill_id: str
    patient_id: str
    amount: float
    status: str  # pending, paid, overdue
    payment_method: str = ""
    issue_date: str = field(default_factory=lambda: datetime.now().isoformat())
    created_date: str = ""
    provider: str = ""
    items: List[Dict[str, Any]] = field(default_factory=list)
    services: str = ""
    appointment_id: str = ""
    due_date: str = ""
    paid_date: str = ""
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class InventoryItem:
    """Inventory item model"""
    item_id: str
    item_name: str
    category: str
    quantity: int
    unit_price: float
    reorder_level: int
    supplier: str = ""
    expiry_date: str = ""
    batch_number: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class User:
    """User model for authentication"""
    user_id: str
    username: str
    email: str
    password_hash: str
    role: str  # admin, doctor, staff, patient
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
