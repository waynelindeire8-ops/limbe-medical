"""
Utility Helper Functions
"""

import uuid
import re
from datetime import datetime
from typing import Optional


class IDGenerator:
    """Generate unique IDs for entities"""
    
    @staticmethod
    def generate_patient_id() -> str:
        """Generate patient ID"""
        return f"PAT-{uuid.uuid4().hex[:8].upper()}"
    
    @staticmethod
    def generate_doctor_id() -> str:
        """Generate doctor ID"""
        return f"DOC-{uuid.uuid4().hex[:8].upper()}"
    
    @staticmethod
    def generate_appointment_id() -> str:
        """Generate appointment ID"""
        return f"APT-{uuid.uuid4().hex[:8].upper()}"
    
    @staticmethod
    def generate_record_id() -> str:
        """Generate medical record ID"""
        return f"REC-{uuid.uuid4().hex[:8].upper()}"
    
    @staticmethod
    def generate_bill_id() -> str:
        """Generate bill ID"""
        return f"BIL-{uuid.uuid4().hex[:8].upper()}"
    
    @staticmethod
    def generate_item_id() -> str:
        """Generate inventory item ID"""
        return f"INV-{uuid.uuid4().hex[:8].upper()}"
    
    @staticmethod
    def generate_user_id() -> str:
        """Generate user ID"""
        return f"USR-{uuid.uuid4().hex[:8].upper()}"


class Validator:
    """Validation utilities"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email address"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number"""
        # Remove common separators
        phone = re.sub(r'[\s\-\(\)\.]+', '', phone)
        # Check if it's a valid phone number (7-15 digits)
        return re.match(r'^\d{7,15}$', phone) is not None
    
    @staticmethod
    def validate_date(date_str: str, format: str = '%Y-%m-%d') -> bool:
        """Validate date format"""
        try:
            datetime.strptime(date_str, format)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_password(password: str, min_length: int = 8) -> bool:
        """Validate password strength"""
        if len(password) < min_length:
            return False
        # Check for uppercase, lowercase, digit, special char
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        return has_upper and has_lower and has_digit


class DateTimeHelper:
    """Date and time utilities"""
    
    @staticmethod
    def get_current_datetime() -> str:
        """Get current datetime in ISO format"""
        return datetime.now().isoformat()
    
    @staticmethod
    def format_date(date_str: str, format: str = '%Y-%m-%d') -> str:
        """Format date string"""
        try:
            date_obj = datetime.fromisoformat(date_str)
            return date_obj.strftime(format)
        except:
            return date_str
    
    @staticmethod
    def get_age(date_of_birth: str) -> int:
        """Calculate age from date of birth"""
        try:
            dob = datetime.fromisoformat(date_of_birth)
            today = datetime.now()
            return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        except:
            return 0


class StatusHelper:
    """Status and color utilities"""
    
    STATUS_COLORS = {
        'pending': '#FFA500',
        'scheduled': '#FFA500',
        'completed': '#4CAF50',
        'cancelled': '#F44336',
        'paid': '#4CAF50',
        'overdue': '#F44336',
        'available': '#4CAF50',
        'unavailable': '#F44336',
    }
    
    @staticmethod
    def get_status_color(status: str) -> str:
        """Get color for status"""
        return StatusHelper.STATUS_COLORS.get(status.lower(), '#999999')
    
    @staticmethod
    def is_valid_status(status: str, entity_type: str) -> bool:
        """Check if status is valid for entity type"""
        valid_statuses = {
            'appointment': ['scheduled', 'completed', 'cancelled'],
            'bill': ['pending', 'paid', 'overdue'],
            'doctor': ['available', 'unavailable'],
        }
        return status.lower() in valid_statuses.get(entity_type, [])
