"""
Database Manager with Supabase Integration
Optimized for Scalability
"""

import json
import sqlite3
import urllib.request
import urllib.error
import threading
import os
from typing import List, Dict, Optional, Any, Type, TypeVar
from datetime import datetime
from dataclasses import asdict, fields
from config.supabase_config import supabase_client, SupabaseConfig
from models import (
    Patient, Doctor, Appointment, MedicalRecord, 
    Prescription, PrescriptionMedication, Bill, InventoryItem, User, Message, QueueItem, LabResult
)

T = TypeVar('T')

class DatabaseManager:
    """Manages database operations with SQLite and Supabase sync"""
    
    def __init__(self, db_file: str = "hospital_data.db", use_supabase: bool = False):
        self.db_file = db_file
        self.use_supabase = use_supabase
        self.last_sync_success = True
        self.last_error = None
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
                scheme_type TEXT,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT DEFAULT ''
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
                status TEXT,
                is_locum INTEGER DEFAULT 0,
                locum_name TEXT DEFAULT ''
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
                date_prescribed TEXT DEFAULT '',
                medication TEXT,
                duration TEXT,
                notes TEXT,
                status TEXT DEFAULT 'Pending',
                record_id TEXT DEFAULT '',
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
                FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prescription_medications (
                med_id TEXT PRIMARY KEY,
                prescription_id TEXT,
                medication_name TEXT,
                dosage TEXT DEFAULT '',
                frequency TEXT DEFAULT '',
                route TEXT DEFAULT '',
                duration TEXT DEFAULT '',
                quantity INTEGER DEFAULT 0,
                refills_allowed INTEGER DEFAULT 0,
                refills_used INTEGER DEFAULT 0,
                notes TEXT DEFAULT '',
                FOREIGN KEY (prescription_id) REFERENCES prescriptions(prescription_id)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rx_med_prescription ON prescription_medications(prescription_id)')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prescription_templates (
                template_id TEXT PRIMARY KEY,
                name TEXT,
                doctor_id TEXT,
                medications TEXT,
                is_global INTEGER DEFAULT 0,
                created_at TEXT
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

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS drafts (
                draft_id TEXT PRIMARY KEY,
                user_id TEXT,
                form_type TEXT,
                data TEXT,
                updated_at TEXT
            )
        ''')
        
        conn.commit()
        
        # Migration: Add columns if they don't exist
        try:
            cursor.execute("ALTER TABLE doctors ADD COLUMN is_locum INTEGER DEFAULT 0")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE doctors ADD COLUMN locum_name TEXT DEFAULT ''")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE patients ADD COLUMN is_deleted INTEGER DEFAULT 0")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE patients ADD COLUMN deleted_at TEXT DEFAULT ''")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE patients ADD COLUMN allergies TEXT DEFAULT ''")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE prescriptions ADD COLUMN date_prescribed TEXT DEFAULT ''")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE prescriptions ADD COLUMN record_id TEXT DEFAULT ''")
        except:
            pass
            
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

    def pull_all_from_supabase(self):
        """Pull all records from Supabase (both Storage JSON and Postgres Tables)"""
        if not self.use_supabase:
            print("[WARN] pull_all_from_supabase: Supabase sync is disabled.")
            return
            
        print("[INFO] Pulling all data from Supabase...")
        
        # Temporarily disable supabase sync during pull to avoid feedback loop
        original_use_supabase = self.use_supabase
        self.use_supabase = False
        
        try:
            # 1. Try pulling from Storage JSON first (contains full metadata + records)
            from supabase_data_manager import get_supabase_json
            cloud_data = get_supabase_json()
            if cloud_data:
                print(f"[INFO] Found JSON backup in storage with {len(cloud_data.get('patients', []))} patients.")
                
                table_models = {
                    'patients': (Patient, 'patient_id'),
                    'doctors': (Doctor, 'doctor_id'),
                    'appointments': (Appointment, 'appointment_id'),
                    'medical_records': (MedicalRecord, 'record_id'),
                    'prescriptions': (Prescription, 'prescription_id'),
                    'prescription_medications': (PrescriptionMedication, 'med_id'),
                    'bills': (Bill, 'bill_id'),
                    'inventory': (InventoryItem, 'item_id'),
                    'users': (User, 'user_id'),
                    'queue': (QueueItem, 'queue_id'),
                    'lab_results': (LabResult, 'result_id')
                }
                
                for table, (model_cls, id_field) in table_models.items():
                    if table in cloud_data:
                        records = cloud_data[table]
                        print(f"  - Syncing {len(records)} {table} from JSON...")
                        for r in records:
                            try:
                                filtered = {k: v for k, v in r.items() if k in {f.name for f in fields(model_cls)}}
                                obj = model_cls(**filtered)
                                
                                # Only save if the record doesn't exist locally to avoid overwriting newer local work
                                id_val = getattr(obj, id_field)
                                if not self.get_by_id(model_cls, table, id_val, id_field):
                                    self.save(table, obj, id_field)
                            except Exception:
                                continue
                
                # DO NOT overwrite local hospital_data.json as it may contain newer local changes
                # if 'settings' in cloud_data: ... (removed)
        except Exception as e:
            print(f"[WARN] Failed to pull from JSON storage: {e}")

        # 2. Try pulling from Postgres Tables (individual records)
        try:
            table_models = {
                'patients': (Patient, 'patient_id'),
                'doctors': (Doctor, 'doctor_id'),
                'appointments': (Appointment, 'appointment_id'),
                'medical_records': (MedicalRecord, 'record_id'),
                'prescriptions': (Prescription, 'prescription_id'),
                'bills': (Bill, 'bill_id'),
                'inventory': (InventoryItem, 'item_id'),
                'users': (User, 'user_id'),
                'queue': (QueueItem, 'queue_id'),
                'lab_results': (LabResult, 'result_id')
            }
            
            for table, (model_cls, id_field) in table_models.items():
                try:
                    supabase_table = SupabaseConfig.TABLES.get(table, table)
                    
                    # Pull in chunks of 1000 to handle large datasets
                    offset = 0
                    chunk_size = 1000
                    while True:
                        records = supabase_client.select(supabase_table, limit=chunk_size, offset=offset)
                        if not records:
                            break
                            
                        print(f"  - Table '{table}': pulled {len(records)} records (offset {offset})")
                        for r in records:
                            try:
                                obj = model_cls(**{k: v for k, v in r.items() if k in {f.name for f in fields(model_cls)}})
                                # Only save if the record doesn't exist locally
                                id_val = getattr(obj, id_field)
                                if not self.get_by_id(model_cls, table, id_val, id_field):
                                    self.save(table, obj, id_field)
                            except Exception:
                                continue
                                
                        if len(records) < chunk_size:
                            break
                        offset += chunk_size
                except Exception as e:
                    print(f"  [ERROR] Failed to pull table {table} from Postgres: {e}")
        finally:
            # Re-enable sync
            self.use_supabase = original_use_supabase

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
                try:
                    supabase_table = SupabaseConfig.TABLES.get(table, table)
                    result = supabase_client.upsert(supabase_table, self._obj_to_dict(obj))
                    
                    if result is None:
                        self.last_sync_success = False
                        self.last_error = f"Supabase sync failed for {table}"
                    elif isinstance(result, dict) and result.get('status') == 'skipped':
                        # Table is missing in Supabase, but JSON backup still works.
                        # We don't mark this as a sync failure to avoid nagging the user.
                        self.last_sync_success = True
                    else:
                        self.last_sync_success = True
                except Exception as e:
                    print(f"[WARN] Supabase upsert failed for {table}: {e}")
                    self.last_sync_success = False
                    self.last_error = str(e)
            
            # Sync to backup server if configured
            self.sync_to_backup(table, obj)
            
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
                try:
                    supabase_table = SupabaseConfig.TABLES.get(table, table)
                    if not supabase_client.delete(supabase_table, id_field, id_value):
                        self.last_sync_success = False
                        self.last_error = f"Supabase delete returned False for {table}"
                    else:
                        self.last_sync_success = True
                except Exception as e:
                    print(f"[WARN] Supabase delete failed for {table}: {e}")
                    self.last_sync_success = False
                    self.last_error = str(e)
            return True
        except Exception as e:
            print(f"Error deleting from {table}: {e}")
            return False

    def delete_all(self, table: str) -> bool:
        """Delete all records from a table"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {table}")
            conn.commit()
            conn.close()
            
            if self.use_supabase:
                # Warning: Supabase delete without filters might be restricted or require special handling
                # depending on the configuration. For now, we focus on SQLite.
                pass
            return True
        except Exception as e:
            print(f"Error deleting all from {table}: {e}")
            return False

    def count(self, table: str, where_clause: str = None, params: tuple = ()) -> int:
        """Efficiently count records in a table"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            where = f"WHERE {where_clause}" if where_clause else ""
            cursor.execute(f"SELECT COUNT(*) FROM {table} {where}", params)
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            print(f"[ERROR] DatabaseManager.count: {e}")
            return 0

    def get_all(self, cls: Type[T], table: str, limit: int = 100, offset: int = 0, order_by: str = None, where_clause: str = None, params: tuple = ()) -> List[T]:
        """Generic get all with pagination, ordering, and optional filtering"""
        try:
            order_clause = f"ORDER BY {order_by}" if order_by else ""
            where_clause = f"WHERE {where_clause}" if where_clause else ""
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table} {where_clause} {order_clause} LIMIT ? OFFSET ?", params + (limit, offset))
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

    # ---------- Drafts & Backup Routing ----------

    def save_draft(self, user_id: str, form_type: str, data: Dict[str, Any]) -> bool:
        """Save a real-time draft of form data"""
        try:
            draft_id = f"{user_id}_{form_type}"
            updated_at = datetime.now().isoformat()
            data_json = json.dumps(data)
            
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO drafts (draft_id, user_id, form_type, data, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (draft_id, user_id, form_type, data_json, updated_at))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving draft: {e}")
            return False

    def get_draft(self, user_id: str, form_type: str) -> Optional[Dict[str, Any]]:
        """Retrieve a saved draft"""
        try:
            draft_id = f"{user_id}_{form_type}"
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM drafts WHERE draft_id = ?", (draft_id,))
            row = cursor.fetchone()
            conn.close()
            return json.loads(row['data']) if row else None
        except Exception as e:
            print(f"Error getting draft: {e}")
            return None

    def delete_draft(self, user_id: str, form_type: str) -> bool:
        """Clear a draft after successful submission"""
        try:
            draft_id = f"{user_id}_{form_type}"
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM drafts WHERE draft_id = ?", (draft_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting draft: {e}")
            return False

    def sync_to_backup(self, table: str, obj: Any):
        """Asynchronously sync data to a backup server if configured"""
        # In a real scenario, this would read from a config or env variable
        backup_url = os.environ.get('BACKUP_SERVER_URL')
        if not backup_url:
            return

        def _perform_sync():
            try:
                data = asdict(obj)
                # Handle JSON fields if any
                for k, v in data.items():
                    if isinstance(v, (dict, list)):
                        data[k] = json.dumps(v)
                
                payload = json.dumps({
                    'table': table,
                    'action': 'save',
                    'data': data,
                    'timestamp': datetime.now().isoformat()
                }).encode('utf-8')
                
                req = urllib.request.Request(
                    backup_url, 
                    data=payload, 
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    pass
            except Exception as e:
                print(f"[BACKUP ERROR] Failed to sync {table} to {backup_url}: {e}")

        # Run in background thread to not block the main application
        threading.Thread(target=_perform_sync, daemon=True).start()

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
