"""
Database Manager with Supabase Integration
"""

import json
import sqlite3
from typing import List, Dict, Optional, Any
from datetime import datetime
from config.supabase_config import supabase_client, SupabaseConfig
from core.models import (
    Patient, Doctor, Appointment, MedicalRecord, 
    Prescription, Bill, InventoryItem, User
)


class DatabaseManager:
    """Manages database operations with SQLite and Supabase sync"""
    
    def __init__(self, db_file: str = "hospital_data.db", use_supabase: bool = True):
        self.db_file = db_file
        self.use_supabase = use_supabase and supabase_client.connect()
        self.init_sqlite_db()
    
    def init_sqlite_db(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                patient_id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                date_of_birth TEXT,
                gender TEXT,
                phone TEXT,
                email TEXT,
                address TEXT,
                emergency_contact TEXT,
                medical_history TEXT,
                allergies TEXT,
                current_medications TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS doctors (
                doctor_id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                specialization TEXT,
                license_number TEXT,
                phone TEXT,
                email TEXT,
                department TEXT,
                availability TEXT,
                years_of_experience INTEGER,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                appointment_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                doctor_id TEXT NOT NULL,
                appointment_date TEXT,
                appointment_time TEXT,
                status TEXT,
                reason TEXT,
                notes TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
                FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS medical_records (
                record_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                doctor_id TEXT NOT NULL,
                visit_date TEXT,
                diagnosis TEXT,
                treatment TEXT,
                prescription TEXT,
                notes TEXT,
                vital_signs TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
                FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bills (
                bill_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                amount REAL,
                status TEXT,
                payment_method TEXT,
                issue_date TEXT,
                due_date TEXT,
                paid_date TEXT,
                description TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                item_id TEXT PRIMARY KEY,
                item_name TEXT NOT NULL,
                category TEXT,
                quantity INTEGER,
                unit_price REAL,
                reorder_level INTEGER,
                supplier TEXT,
                expiry_date TEXT,
                batch_number TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    # Patient Operations
    def add_patient(self, patient: Dict[str, Any]) -> bool:
        """Add patient to database"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO patients VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                patient['patient_id'], patient['first_name'], patient['last_name'],
                patient['date_of_birth'], patient['gender'], patient['phone'],
                patient['email'], patient['address'], patient.get('emergency_contact', ''),
                patient.get('medical_history', ''), patient.get('allergies', ''),
                patient.get('current_medications', ''), datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            # Sync to Supabase
            if self.use_supabase:
                supabase_client.insert('patients', patient)
            
            return True
        except Exception as e:
            print(f"Error adding patient: {str(e)}")
            return False
    
    def get_all_patients(self) -> List[Dict]:
        """Get all patients"""
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM patients')
            patients = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return patients
        except Exception as e:
            print(f"Error getting patients: {str(e)}")
            return []
    
    def get_patient(self, patient_id: str) -> Optional[Dict]:
        """Get patient by ID"""
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM patients WHERE patient_id = ?', (patient_id,))
            patient = cursor.fetchone()
            
            conn.close()
            return dict(patient) if patient else None
        except Exception as e:
            print(f"Error getting patient: {str(e)}")
            return None
    
    def update_patient(self, patient_id: str, data: Dict[str, Any]) -> bool:
        """Update patient"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            set_clause = ', '.join([f'{k} = ?' for k in data.keys()] + ['updated_at = ?'])
            values = list(data.values()) + [datetime.now().isoformat(), patient_id]
            
            cursor.execute(f'UPDATE patients SET {set_clause} WHERE patient_id = ?',
                         values)
            
            conn.commit()
            conn.close()
            
            # Sync to Supabase
            if self.use_supabase:
                supabase_client.update('patients', 'patient_id', patient_id, data)
            
            return True
        except Exception as e:
            print(f"Error updating patient: {str(e)}")
            return False
    
    def delete_patient(self, patient_id: str) -> bool:
        """Delete patient"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM patients WHERE patient_id = ?', (patient_id,))
            
            conn.commit()
            conn.close()
            
            # Sync to Supabase
            if self.use_supabase:
                supabase_client.delete('patients', 'patient_id', patient_id)
            
            return True
        except Exception as e:
            print(f"Error deleting patient: {str(e)}")
            return False
    
    def search_patients(self, search_term: str) -> List[Dict]:
        """Search patients by name or ID"""
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM patients 
                WHERE patient_id LIKE ? OR first_name LIKE ? OR last_name LIKE ?
            ''', (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
            
            patients = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return patients
        except Exception as e:
            print(f"Error searching patients: {str(e)}")
            return []
    
    # Doctor Operations
    def add_doctor(self, doctor: Dict[str, Any]) -> bool:
        """Add doctor to database"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO doctors VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                doctor['doctor_id'], doctor['first_name'], doctor['last_name'],
                doctor['specialization'], doctor['license_number'], doctor['phone'],
                doctor['email'], doctor['department'], doctor.get('availability', 'Available'),
                doctor.get('years_of_experience', 0), datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            if self.use_supabase:
                supabase_client.insert('doctors', doctor)
            
            return True
        except Exception as e:
            print(f"Error adding doctor: {str(e)}")
            return False
    
    def get_all_doctors(self) -> List[Dict]:
        """Get all doctors"""
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM doctors')
            doctors = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return doctors
        except Exception as e:
            print(f"Error getting doctors: {str(e)}")
            return []
    
    # Appointment Operations
    def add_appointment(self, appointment: Dict[str, Any]) -> bool:
        """Add appointment"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO appointments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                appointment['appointment_id'], appointment['patient_id'],
                appointment['doctor_id'], appointment['appointment_date'],
                appointment['appointment_time'], appointment.get('status', 'scheduled'),
                appointment.get('reason', ''), appointment.get('notes', ''),
                datetime.now().isoformat(), datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            if self.use_supabase:
                supabase_client.insert('appointments', appointment)
            
            return True
        except Exception as e:
            print(f"Error adding appointment: {str(e)}")
            return False
    
    def get_all_appointments(self) -> List[Dict]:
        """Get all appointments"""
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM appointments')
            appointments = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return appointments
        except Exception as e:
            print(f"Error getting appointments: {str(e)}")
            return []
    
    # Medical Record Operations
    def add_medical_record(self, record: Dict[str, Any]) -> bool:
        """Add medical record"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO medical_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record['record_id'], record['patient_id'], record['doctor_id'],
                record['visit_date'], record['diagnosis'], record['treatment'],
                record.get('prescription', ''), record.get('notes', ''),
                record.get('vital_signs', ''), datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            if self.use_supabase:
                supabase_client.insert('medical_records', record)
            
            return True
        except Exception as e:
            print(f"Error adding medical record: {str(e)}")
            return False
    
    def get_all_medical_records(self) -> List[Dict]:
        """Get all medical records"""
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM medical_records')
            records = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return records
        except Exception as e:
            print(f"Error getting medical records: {str(e)}")
            return []
    
    # Bill Operations
    def add_bill(self, bill: Dict[str, Any]) -> bool:
        """Add bill"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO bills VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                bill['bill_id'], bill['patient_id'], bill['amount'],
                bill.get('status', 'pending'), bill.get('payment_method', ''),
                bill.get('issue_date', datetime.now().isoformat()),
                bill.get('due_date', ''), bill.get('paid_date', ''),
                bill.get('description', ''), datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            if self.use_supabase:
                supabase_client.insert('bills', bill)
            
            return True
        except Exception as e:
            print(f"Error adding bill: {str(e)}")
            return False
    
    def get_all_bills(self) -> List[Dict]:
        """Get all bills"""
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM bills')
            bills = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return bills
        except Exception as e:
            print(f"Error getting bills: {str(e)}")
            return []
    
    # Inventory Operations
    def add_inventory_item(self, item: Dict[str, Any]) -> bool:
        """Add inventory item"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO inventory VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item['item_id'], item['item_name'], item['category'],
                item['quantity'], item['unit_price'], item['reorder_level'],
                item.get('supplier', ''), item.get('expiry_date', ''),
                item.get('batch_number', ''), datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            if self.use_supabase:
                supabase_client.insert('inventory', item)
            
            return True
        except Exception as e:
            print(f"Error adding inventory item: {str(e)}")
            return False
    
    def get_all_inventory(self) -> List[Dict]:
        """Get all inventory items"""
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM inventory')
            items = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return items
        except Exception as e:
            print(f"Error getting inventory: {str(e)}")
            return []
    
    def get_low_stock_items(self, threshold: int = None) -> List[Dict]:
        """Get items with low stock"""
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM inventory WHERE quantity <= reorder_level')
            items = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return items
        except Exception as e:
            print(f"Error getting low stock items: {str(e)}")
            return []
