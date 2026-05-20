"""
Database Manager with Supabase Integration
Optimized for Scalability
"""

import json
import sqlite3
from typing import List, Dict, Optional, Any, Type, TypeVar
from datetime import datetime
from dataclasses import asdict, fields
from config.supabase_config import supabase_client, SupabaseConfig
from models import (
    Patient, Doctor, Appointment, MedicalRecord, 
    Prescription, Bill, InventoryItem, User, Message, QueueItem, LabResult
)

T = TypeVar('T')

class DatabaseManager:
    """Manages database operations with SQLite and Supabase sync"""
    
    def __init__(self, db_file: str = "hospital_data.db", use_supabase: bool = False):
        self.db_file = db_file
        self.use_supabase = use_supabase
        self.init_sqlite_db()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn

    def init_sqlite_db(self):
        """Initialize SQLite database with tables and indexes"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                patient_id TEXT PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                date_of_birth TEXT,
                gender TEXT,
                phone TEXT,
                email TEXT,
                address TEXT,
                emergency_contact TEXT,
                blood_group TEXT,
                medical_history TEXT,
                created_date TEXT,
                scheme_provider TEXT,
                scheme_type TEXT
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_patient_name ON patients(first_name, last_name)')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS doctors (
                doctor_id TEXT PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                specialty TEXT,
                phone TEXT,
                email TEXT,
                schedule TEXT,
                status TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                appointment_id TEXT PRIMARY KEY,
                patient_id TEXT,
                doctor_id TEXT,
                appointment_date TEXT,
                appointment_time TEXT,
                reason TEXT,
                status TEXT,
                notes TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
                FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_appointment_date ON appointments(appointment_date)')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS medical_records (
                record_id TEXT PRIMARY KEY,
                patient_id TEXT,
                doctor_id TEXT,
                date TEXT,
                consult_reason TEXT,
                diagnosis TEXT,
                treatment TEXT,
                prescriptions TEXT,
                notes TEXT,
                details TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
                FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prescriptions (
                prescription_id TEXT PRIMARY KEY,
                patient_id TEXT,
                doctor_id TEXT,
                date TEXT,
                medication TEXT,
                duration TEXT,
                notes TEXT,
                status TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
                FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bills (
                bill_id TEXT PRIMARY KEY,
                patient_id TEXT,
                appointment_id TEXT,
                amount REAL,
                services TEXT,
                status TEXT,
                created_date TEXT,
                provider TEXT,
                items TEXT,
                created_at TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                item_id TEXT PRIMARY KEY,
                name TEXT,
                category TEXT,
                quantity INTEGER,
                unit_price REAL,
                supplier TEXT,
                expiry_date TEXT,
                min_quantity INTEGER,
                dosage_form TEXT,
                strength TEXT,
                batch_number TEXT,
                notes TEXT,
                is_medicine INTEGER,
                billing_codes TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                password_salt TEXT,
                password_hash TEXT,
                role TEXT,
                is_active INTEGER,
                is_verified INTEGER,
                otp_enabled INTEGER,
                otp_secret TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                sender_id TEXT,
                sender_name TEXT,
                recipient_id TEXT,
                subject TEXT,
                content TEXT,
                timestamp TEXT,
                is_read INTEGER,
                is_archived INTEGER
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS queue (
                queue_id TEXT PRIMARY KEY,
                patient_id TEXT,
                patient_name TEXT,
                doctor_id TEXT,
                status TEXT,
                priority TEXT,
                arrival_time TEXT,
                estimated_wait TEXT,
                department TEXT,
                visit_reason TEXT,
                special_category TEXT,
                check_in_time TEXT,
                assigned_doctor_id TEXT,
                doctor_name TEXT,
                triage_level TEXT,
                date_added TEXT,
                vitals TEXT,
                assigned_nurse_id TEXT,
                last_called_time TEXT,
                requeued_count INTEGER,
                notes TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lab_results (
                result_id TEXT PRIMARY KEY,
                patient_id TEXT,
                doctor_id TEXT,
                test_name TEXT,
                test_date TEXT,
                result_value TEXT,
                units TEXT,
                reference_range TEXT,
                status TEXT,
                notes TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def _row_to_obj(self, cls: Type[T], row: sqlite3.Row) -> T:
        """Convert a SQLite row to a dataclass object"""
        d = dict(row)
        # Handle JSON fields
        for field in fields(cls):
            if field.type in (dict, Dict[str, Any], list, List[Any]) and d.get(field.name):
                try:
                    d[field.name] = json.loads(d[field.name])
                except:
                    pass
            elif field.type == bool and field.name in d:
                d[field.name] = bool(d[field.name])
        
        # Filter only fields that exist in the dataclass
        allowed = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in d.items() if k in allowed}
        return cls(**filtered)

    def _obj_to_dict(self, obj: Any) -> Dict[str, Any]:
        """Convert a dataclass object to a dict, handling JSON fields"""
        d = asdict(obj)
        for k, v in d.items():
            if isinstance(v, (dict, list)):
                d[k] = json.dumps(v)
            elif isinstance(v, bool):
                d[k] = 1 if v else 0
        return d

    def save(self, table: str, obj: Any, id_field: str) -> bool:
        """Generic save (insert or replace)"""
        try:
            data = self._obj_to_dict(obj)
            cols = ', '.join(data.keys())
            placeholders = ', '.join(['?'] * len(data))
            
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(f"INSERT OR REPLACE INTO {table} ({cols}) VALUES ({placeholders})", list(data.values()))
            conn.commit()
            conn.close()
            
            if self.use_supabase:
                supabase_client.insert(table, asdict(obj)) # Supabase handles dicts/lists
            return True
        except Exception as e:
            print(f"Error saving to {table}: {e}")
            return False

    def delete(self, table: str, id_value: str, id_field: str) -> bool:
        """Generic delete"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {table} WHERE {id_field} = ?", (id_value,))
            conn.commit()
            conn.close()
            
            if self.use_supabase:
                supabase_client.delete(table, id_field, id_value)
            return True
        except Exception as e:
            print(f"Error deleting from {table}: {e}")
            return False

    def get_all(self, cls: Type[T], table: str, limit: int = 100, offset: int = 0) -> List[T]:
        """Generic get all with pagination"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table} LIMIT ? OFFSET ?", (limit, offset))
            rows = cursor.fetchall()
            conn.close()
            return [self._row_to_obj(cls, row) for row in rows]
        except Exception as e:
            print(f"Error getting from {table}: {e}")
            return []

    def get_by_id(self, cls: Type[T], table: str, id_value: str, id_field: str) -> Optional[T]:
        """Generic get by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table} WHERE {id_field} = ?", (id_value,))
            row = cursor.fetchone()
            conn.close()
            return self._row_to_obj(cls, row) if row else None
        except Exception as e:
            print(f"Error getting from {table}: {e}")
            return None

    def count(self, table: str) -> int:
        """Get total count of records in a table"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            print(f"Error counting {table}: {e}")
            return 0

    def search(self, cls: Type[T], table: str, query: str, fields: List[str], limit: int = 50) -> List[T]:
        """Generic search with multiple fields"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            where_clause = ' OR '.join([f"{f} LIKE ?" for f in fields])
            params = [f"%{query}%"] * len(fields)
            cursor.execute(f"SELECT * FROM {table} WHERE {where_clause} LIMIT ?", params + [limit])
            rows = cursor.fetchall()
            conn.close()
            return [self._row_to_obj(cls, row) for row in rows]
        except Exception as e:
            print(f"Error searching {table}: {e}")
            return []
