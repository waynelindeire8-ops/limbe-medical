#!/usr/bin/env python3
"""
Limbe Medical Clinic - Hospital Management System
-------------------------------------------------
A comprehensive system for managing patients, doctors, appointments,
medical records, billing, and inventory data.

This module serves as the backend logic and data layer for the GUI.
"""

import os
import json
import re
import uuid
try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv():
        return False
from supabase_data_manager import (
    get_supabase_json, 
    put_supabase_json, 
    list_files_in_supabase_folder, 
    get_supabase_file_url,
    upload_file_to_supabase,
    delete_file_from_supabase
)

load_dotenv()
import datetime
import hashlib
import shutil
import urllib.request
import urllib.error

from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any
from models import Patient, Doctor, Appointment, MedicalRecord, Prescription, Bill, InventoryItem, User, Message, QueueItem, LabResult


from database.db_manager import DatabaseManager


# ==============================
# 🏥 HOSPITAL MANAGEMENT SYSTEM
# ==============================

class HospitalManagementSystem:
    """Core class for managing hospital data and operations."""

    def __init__(self, data_file: str = "hospital_data.json", db_file: str = "hospital_data.db"):
        self.data_file = data_file
        self.db_file = db_file
        self.db = DatabaseManager(db_file=db_file)

        # Cache settings for fast access, other data stays in DB
        self.settings: Dict[str, Any] = {
            'theme': 'Light',
            'notifications': True,
            'auto_backup': False,
            'language': 'English',
            'date_format': 'DD/MM/YYYY',
            'server_url': None,
            'supabase_project_id': os.environ.get('SUPABASE_PROJECT_ID', 'qiudxdvssvkbpoovwpbr'),
            'supabase_url': os.environ.get('SUPABASE_URL', 'https://qiudxdvssvkbpoovwpbr.supabase.co'),
            'supabase_api_key': os.environ.get('SUPABASE_API_KEY', ''),
            'supabase_service_role': os.environ.get('SUPABASE_SERVICE_ROLE', ''),
        }

        # The following are kept for backward compatibility but should be migrated to DB queries
        self._patients_cache: List[Patient] = []
        self._doctors_cache: List[Doctor] = []
        self._appointments_cache: List[Appointment] = []
        self._medical_records_cache: List[MedicalRecord] = []
        self._prescriptions_cache: List[Prescription] = []
        self._bills_cache: List[Bill] = []
        self._inventory_cache: List[InventoryItem] = []
        self._users_cache: List[User] = []
        self._messages_cache: List[Message] = []
        self._queue_cache: List[QueueItem] = []
        self._lab_results_cache: List[LabResult] = []

        self.activity: List[Dict[str, Any]] = []
        self.patient_files: Dict[str, List[Dict[str, Any]]] = {}
        self.patient_scheme: Dict[str, Dict[str, Any]] = {}
        self.departments: List[str] = []

        # Route data file to OneDrive if available
        onedrive_path = self._route_data_file_to_onedrive(os.path.basename(self.data_file))
        if onedrive_path:
            if os.path.exists(self.data_file) and not os.path.exists(onedrive_path):
                try:
                    shutil.copy2(self.data_file, onedrive_path)
                except Exception:
                    pass
            self.data_file = onedrive_path

        self.load_data()

        # Check for legacy data migration — skipped automatically if DB already has data
        self._migrate_json_to_db()

    @property
    def patients(self) -> List[Patient]:
        return self.db.get_all(Patient, 'patients', limit=10000, order_by='rowid DESC', where_clause="is_deleted = 0")

    def get_patients_paginated(self, page: int = 1, per_page: int = 20) -> List[Patient]:
        return self.db.get_all(Patient, 'patients', limit=per_page, offset=(page-1)*per_page, order_by='rowid DESC', where_clause="is_deleted = 0")

    def get_patients_count(self) -> int:
        return self.db.count('patients', "is_deleted = 0")

    def get_deleted_patients(self) -> List[Patient]:
        """Get all soft-deleted patients for recovery."""
        return self.db.get_all(Patient, 'patients', limit=10000, order_by='deleted_at DESC', where_clause="is_deleted = 1")

    def recover_patient(self, patient_id: str) -> bool:
        """Recover a soft-deleted patient."""
        patient = self.db.get_by_id(Patient, 'patients', patient_id, 'patient_id')
        if patient:
            patient.is_deleted = 0
            patient.deleted_at = ""
            if self.db.save('patients', patient, 'patient_id'):
                try:
                    self.add_activity(None, 'recover', 'patient', patient_id, f"Recovered patient {patient_id}")
                except Exception:
                    pass
                return True
        return False

    def sync_patient_attachments(self, patient_id: str) -> int:
        """Discovers files in Supabase storage for a patient and updates metadata."""
        if not patient_id:
            return 0
            
        print(f"[INFO] Syncing attachments for patient {patient_id}...")
        supabase_files = list_files_in_supabase_folder(patient_id)
        if not supabase_files:
            return 0
            
        existing_entries = self.patient_files.get(patient_id, [])
        existing_names = {e['file_name'] for e in existing_entries}
        
        added = 0
        for f in supabase_files:
            if f['name'] not in existing_names:
                # This file is in Supabase but not in our local metadata
                rel_path = f"attachments/{patient_id}/{f['name']}"
                existing_entries.append({
                    'file_name': f['name'],
                    'path': rel_path,
                    'uploaded_at': f['created_at'].replace('T', ' ').split('.')[0], # Simple format
                    'source_appointment_id': '',
                    'source_record_id': '',
                    'supabase_file_id': '',
                    'is_remote': True, # Flag to indicate it might not be on local disk
                    'url': get_supabase_file_url(rel_path)
                })
                added += 1
                
        if added > 0:
            self.patient_files[patient_id] = existing_entries
            self.save_data()
            print(f"[INFO] Discovered {added} new attachments for {patient_id}")
            
        return added

    def get_doctors_count(self) -> int:
        return self.db.count('doctors')

    def get_appointments_count(self, date: str = None) -> int:
        if date:
            return self.db.count('appointments', "appointment_date = ?", (date,))
        return self.db.count('appointments')

    def get_bills_count(self, status: str = None) -> int:
        if status:
            return self.db.count('bills', "status = ?", (status,))
        return self.db.count('bills')

    def get_medical_records_count(self) -> int:
        return self.db.count('medical_records')

    def get_low_stock_count(self) -> int:
        return self.db.count('inventory', "quantity <= min_quantity")

    @property
    def doctors(self) -> List[Doctor]:
        return self.db.get_all(Doctor, 'doctors', limit=10000)

    @property
    def appointments(self) -> List[Appointment]:
        return self.db.get_all(Appointment, 'appointments', limit=10000)

    @property
    def medical_records(self) -> List[MedicalRecord]:
        return self.db.get_all(MedicalRecord, 'medical_records', limit=10000)

    @property
    def prescriptions(self) -> List[Prescription]:
        return self.db.get_all(Prescription, 'prescriptions', limit=10000)

    @property
    def bills(self) -> List[Bill]:
        return self.db.get_all(Bill, 'bills', limit=10000)

    @property
    def inventory(self) -> List[InventoryItem]:
        return self.db.get_all(InventoryItem, 'inventory', limit=10000)

    @property
    def users(self) -> List[User]:
        return self.db.get_all(User, 'users', limit=10000)

    @property
    def messages(self) -> List[Message]:
        return self.db.get_all(Message, 'messages', limit=10000)

    @property
    def queue(self) -> List[QueueItem]:
        return self.db.get_all(QueueItem, 'queue', limit=10000)

    @queue.setter
    def queue(self, value: List[QueueItem]):
        conn = self.db.get_connection()
        conn.execute("DELETE FROM queue")
        conn.commit()
        conn.close()
        for item in value:
            self.db.save('queue', item, 'queue_id')

    @property
    def lab_results(self) -> List[LabResult]:
        return self.db.get_all(LabResult, 'lab_results', limit=10000)

    def _migrate_json_to_db(self):
        """
        Always migrate legacy JSON data into SQLite.

        Safe behavior:
        - Imports JSON every startup
        - Skips records already existing in DB
        - Prevents overwriting newer SQLite data
        """

        print("[Migration] Running legacy JSON migration...")

        self._patients_cache = []
        self._doctors_cache = []
        self._appointments_cache = []
        self._medical_records_cache = []
        self._prescriptions_cache = []
        self._bills_cache = []
        self._inventory_cache = []
        self._users_cache = []
        self._messages_cache = []
        self._queue_cache = []
        self._lab_results_cache = []

        migrated = False
    
        # =========================
        # 1. Single JSON file
        # =========================
        if os.path.exists(self.data_file):
            print(f"[Migration] Checking: {self.data_file}")
    
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
    
                if data.get('patients'):
                    self._apply_loaded_data(data, append=True)
                    migrated = True
    
            except Exception as e:
                print(f"[Migration] Failed reading {self.data_file}: {e}")
    
        # =========================
        # 2. Legacy directories
        # =========================
        legacy_dirs = ['data', 'sample_data']
    
        for d in legacy_dirs:
    
            if not os.path.exists(d):
                continue
    
            try:
                patients_path = os.path.join(d, 'patients.json')
    
                if not os.path.exists(patients_path):
                    continue
    
                with open(patients_path, 'r', encoding='utf-8') as f:
                    json_patients = json.load(f)
    
                if not json_patients:
                    continue
    
                print(f"[Migration] Found legacy data in {d}")
    
                legacy_data = {}
    
                files = {
                    'patients': 'patients.json',
                    'doctors': 'doctors.json',
                    'appointments': 'appointments.json',
                    'medical_records': 'medical_records.json',
                    'prescriptions': 'prescriptions.json',
                    'bills': 'bills.json',
                    'inventory': 'inventory.json',
                    'users': 'users.json',
                    'messages': 'messages.json',
                    'queue': 'queue.json',
                    'lab_results': 'lab_results.json'
                }
    
                for key, filename in files.items():
    
                    path = os.path.join(d, filename)
    
                    if os.path.exists(path):
    
                        with open(path, 'r', encoding='utf-8') as f:
                            legacy_data[key] = json.load(f)
    
                self._apply_loaded_data(legacy_data, append=True)
    
                migrated = True
    
            except Exception as e:
                print(f"[Migration] Error in {d}: {e}")
    
        # =========================
        # Save safely
        # =========================
        if migrated:
    
            self._save_caches_to_db_safe()
    
            print(
                f"[Migration] Done. Patients in DB: "
                f"{self.db.count('patients')}"
            )
    
        else:
            print("[Migration] No legacy data found.")

    
    def _save_caches_to_db_safe(self):
        """
        Save only records that do not already exist.
        Prevents overwriting live DB data.
        """
    
        def save_if_missing(table, obj, key_field, cls):
    
            key = getattr(obj, key_field)
    
            existing = self.db.get_by_id(
                cls,
                table,
                key,
                key_field
            )
    
            if not existing:
                self.db.save(table, obj, key_field)
    
        # =========================
        # Patients
        # =========================
        for p in self._patients_cache:
            save_if_missing(
                'patients',
                p,
                'patient_id',
                Patient
            )
    
        # =========================
        # Doctors
        # =========================
        for d in self._doctors_cache:
            save_if_missing(
                'doctors',
                d,
                'doctor_id',
                Doctor
            )
    
        # =========================
        # Appointments
        # =========================
        for a in self._appointments_cache:
            save_if_missing(
                'appointments',
                a,
                'appointment_id',
                Appointment
            )
    
        # =========================
        # Medical Records
        # =========================
        for m in self._medical_records_cache:
            save_if_missing(
                'medical_records',
                m,
                'record_id',
                MedicalRecord
            )
    
        # =========================
        # Prescriptions
        # =========================
        for pr in self._prescriptions_cache:
            save_if_missing(
                'prescriptions',
                pr,
                'prescription_id',
                Prescription
            )
    
        # =========================
        # Bills
        # =========================
        for b in self._bills_cache:
            save_if_missing(
                'bills',
                b,
                'bill_id',
                Bill
            )
    
        # =========================
        # Inventory
        # =========================
        for i in self._inventory_cache:
            save_if_missing(
                'inventory',
                i,
                'item_id',
                InventoryItem
            )
    
        # =========================
        # Users
        # =========================
        for u in self._users_cache:
            save_if_missing(
                'users',
                u,
                'user_id',
                User
            )
    
        # =========================
        # Messages
        # =========================
        for msg in self._messages_cache:
            save_if_missing(
                'messages',
                msg,
                'message_id',
                Message
            )
    
        # =========================
        # Queue
        # =========================
        for q in self._queue_cache:
            save_if_missing(
                'queue',
                q,
                'queue_id',
                QueueItem
            )
    
        # =========================
        # Lab Results
        # =========================
        for lr in self._lab_results_cache:
            save_if_missing(
                'lab_results',
                lr,
                'result_id',
                LabResult
            )
    
    # ---------- Utility ----------
    @staticmethod
    def generate_id(prefix: str) -> str:
        """Generate a unique ID with a prefix."""
        return f"{prefix}{str(uuid.uuid4())[:8]}"

    # ---------- Persistence ----------
    def save_data(self) -> None:
        """Save non-relational metadata to JSON. Relational data lives in SQLite."""
        try:
            data = {
                'settings': self.settings,
                'activity': self.activity,
                'patient_files': self.patient_files,
                'patient_scheme': self.patient_scheme,
                'departments': self.departments
            }

            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            # Sync with Supabase if enabled
            if self.db.use_supabase:
                try:
                    from supabase_data_manager import put_supabase_json
                    put_supabase_json(data)
                except Exception as e:
                    print(f"[WARN] Supabase sync failed: {e}")

        except Exception as e:
            print(f"[ERROR] Failed to save data: {e}")

    def load_data(self) -> None:
        """Load metadata from JSON file."""
        if not os.path.exists(self.data_file):
            return

        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._apply_metadata(data)
        except Exception as e:
            print(f"[ERROR] Failed to load data from {self.data_file}: {e}")

    def _apply_metadata(self, data: Dict[str, Any]) -> None:
        """Apply metadata from loaded JSON."""
        self.settings.update(data.get('settings', {}))
        self.activity = data.get('activity', [])
        self.patient_files = data.get('patient_files', {})
        self.patient_scheme = data.get('patient_scheme', {})
        self.departments = data.get('departments', [])

    def _apply_loaded_data(self, data: Dict[str, Any], append: bool = False) -> None:
        """Legacy method for migration — applies all data to temporary caches."""
        from dataclasses import fields as _dc_fields

        def _filter(cls, obj: Dict[str, Any]) -> Dict[str, Any]:
            allowed = {f.name for f in _dc_fields(cls)}
            return {k: v for k, v in obj.items() if k in allowed}

        def _normalize_appointment(obj: Dict[str, Any]) -> Dict[str, Any]:
            tmp = dict(obj)
            if 'date' in tmp and 'appointment_date' not in tmp:
                tmp['appointment_date'] = tmp.pop('date')
            if 'time' in tmp and 'appointment_time' not in tmp:
                tmp['appointment_time'] = tmp.pop('time')
            return _filter(Appointment, tmp)

        def _normalize_bill(obj: Dict[str, Any]) -> Dict[str, Any]:
            tmp = dict(obj)
            if 'date' in tmp and 'created_date' not in tmp:
                tmp['created_date'] = tmp.pop('date')
            if 'payment_status' in tmp and 'status' not in tmp:
                tmp['status'] = tmp.pop('payment_status')
            return _filter(Bill, tmp)

        def _normalize_record(obj: Dict[str, Any]) -> Dict[str, Any]:
            tmp = dict(obj)
            core_fields = {'record_id', 'patient_id', 'doctor_id', 'date', 'consult_reason', 'diagnosis', 'treatment', 'prescriptions', 'notes'}
            new_record = {}
            details = {}
            for key, value in tmp.items():
                if key in core_fields:
                    new_record[key] = value
                elif key != 'details':
                    details[key] = value
                elif key == 'details' and isinstance(value, dict):
                    details.update(value)
            new_record['details'] = details
            return _filter(MedicalRecord, new_record)

        new_patients = [Patient(**_filter(Patient, p)) for p in data.get('patients', [])]
        new_doctors = [Doctor(**_filter(Doctor, d)) for d in data.get('doctors', [])]
        new_appointments = [Appointment(**_normalize_appointment(a)) for a in data.get('appointments', [])]
        new_records = [MedicalRecord(**_normalize_record(m)) for m in data.get('medical_records', [])]
        new_prescriptions = [Prescription(**_filter(Prescription, p)) for p in data.get('prescriptions', [])]
        new_bills = [Bill(**_normalize_bill(b)) for b in data.get('bills', [])]
        new_inventory = [InventoryItem(**_filter(InventoryItem, i)) for i in data.get('inventory', [])]
        new_users = [User(**_filter(User, u)) for u in data.get('users', [])]
        new_messages = [Message(**_filter(Message, m)) for m in data.get('messages', [])]
        new_queue = [QueueItem(**_filter(QueueItem, q)) for q in data.get('queue', [])]
        new_lab_results = [LabResult(**_filter(LabResult, lr)) for lr in data.get('lab_results', [])]

        if append:
            self._patients_cache.extend(new_patients)
            self._doctors_cache.extend(new_doctors)
            self._appointments_cache.extend(new_appointments)
            self._medical_records_cache.extend(new_records)
            self._prescriptions_cache.extend(new_prescriptions)
            self._bills_cache.extend(new_bills)
            self._inventory_cache.extend(new_inventory)
            self._users_cache.extend(new_users)
            self._messages_cache.extend(new_messages)
            self._queue_cache.extend(new_queue)
            self._lab_results_cache.extend(new_lab_results)
        else:
            self._patients_cache = new_patients
            self._doctors_cache = new_doctors
            self._appointments_cache = new_appointments
            self._medical_records_cache = new_records
            self._prescriptions_cache = new_prescriptions
            self._bills_cache = new_bills
            self._inventory_cache = new_inventory
            self._users_cache = new_users
            self._messages_cache = new_messages
            self._queue_cache = new_queue
            self._lab_results_cache = new_lab_results

        self._apply_metadata(data)

    def add_patient_files(self, patient_id: str, file_paths: List[str], source_appointment_id: Optional[str] = None, source_record_id: Optional[str] = None) -> int:
        added = 0
        if not patient_id or not file_paths:
            return added
        base_dir = os.path.dirname(os.path.abspath(self.data_file))
        dest_dir = os.path.join(base_dir, 'attachments', patient_id)
        try:
            os.makedirs(dest_dir, exist_ok=True)
        except Exception:
            pass
        entries = self.patient_files.get(patient_id, [])
        ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for src in file_paths:
            try:
                name = os.path.basename(src)
                dest = os.path.join(dest_dir, name)
                if os.path.exists(dest):
                    root, ext = os.path.splitext(name)
                    name = f"{root}_{int(datetime.datetime.now().timestamp())}{ext}"
                    dest = os.path.join(dest_dir, name)
                
                # Copy locally
                shutil.copy2(src, dest)
                rel_path = os.path.relpath(dest, base_dir)
                
                # Upload to Supabase
                sup_path = f"{patient_id}/{name}"
                upload_file_to_supabase(dest, sup_path)
                
                entries.append({
                    'file_name': name,
                    'path': rel_path,
                    'uploaded_at': ts,
                    'source_appointment_id': source_appointment_id or '',
                    'source_record_id': source_record_id or '',
                    'supabase_file_id': sup_path,
                    'url': get_supabase_file_url(rel_path)
                })
                added += 1
            except Exception as e:
                print(f"[WARN] Failed to add file '{src}': {e}")
        self.patient_files[patient_id] = entries
        self.save_data()
        try:
            self.add_activity(None, 'attach_files', 'patient', patient_id, f"{added} file(s)")
        except Exception:
            pass
        return added

    def delete_patient_file(self, patient_id: str, rel_path: str) -> bool:
        if not patient_id or not rel_path:
            return False
        base_dir = os.path.dirname(os.path.abspath(self.data_file))
        abs_path = os.path.join(base_dir, rel_path)
        entries = self.patient_files.get(patient_id, []) or []
        
        # Find entry to get filename for Supabase
        entry = next((e for e in entries if e.get('path') == rel_path), None)
        
        new_entries = [e for e in entries if e.get('path') != rel_path]
        if len(new_entries) == len(entries):
            return False
            
        try:
            # Delete locally
            if os.path.exists(abs_path):
                os.remove(abs_path)
            
            # Delete from Supabase
            if entry:
                filename = entry.get('file_name')
                delete_file_from_supabase(f"{patient_id}/{filename}")
        except Exception as e:
            print(f"[WARN] Failed to delete file '{abs_path}': {e}")
            
        self.patient_files[patient_id] = new_entries
        self.save_data()
        try:
            self.add_activity(None, 'delete_file', 'patient', patient_id, rel_path)
        except Exception:
            pass
        return True

    def rename_patient_file(self, patient_id: str, rel_path: str, new_name: str) -> bool:
        if not patient_id or not rel_path or not (new_name or '').strip():
            return False
        base_dir = os.path.dirname(os.path.abspath(self.data_file))
        abs_path = os.path.join(base_dir, rel_path)
        entries = self.patient_files.get(patient_id, []) or []
        entry = next((e for e in entries if e.get('path') == rel_path), None)
        if not entry:
            return False
        dest_dir = os.path.dirname(abs_path)
        root, ext = os.path.splitext(new_name)
        if not ext:
            _, old_ext = os.path.splitext(entry.get('file_name', ''))
            new_name = root + old_ext
        new_abs = os.path.join(dest_dir, new_name)
        if os.path.exists(new_abs):
            r, e = os.path.splitext(new_name)
            new_name = f"{r}_{int(datetime.datetime.now().timestamp())}{e}"
            new_abs = os.path.join(dest_dir, new_name)
        try:
            os.replace(abs_path, new_abs)
        except Exception as e:
            print(f"[WARN] Failed to rename file '{abs_path}' -> '{new_abs}': {e}")
            return False
        new_rel = os.path.relpath(new_abs, base_dir)
        entry['file_name'] = new_name
        entry['path'] = new_rel
        self.save_data()
        try:
            self.add_activity(None, 'rename_file', 'patient', patient_id, f"{rel_path} -> {new_rel}")
        except Exception:
            pass
        return True

    def update_patient_scheme(self, patient_id: str, scheme_info: Dict[str, Any]) -> bool:
        if not patient_id:
            return False
        self.patient_scheme[patient_id] = scheme_info or {}
        self.save_data()
        try:
            self.add_activity(None, 'update_scheme', 'patient', patient_id, scheme_info.get('scheme_name', ''))
        except Exception:
            pass
        return True

    def get_patient_scheme(self, patient_id: str) -> Dict[str, Any]:
        return self.patient_scheme.get(patient_id, {})

    # ---------- Patients ----------
    def add_patient(self, patient: Patient) -> bool:
        if not patient.patient_id:
            print("[ERROR] add_patient: patient_id is required")
            return False
            
        # The db.save uses INSERT OR REPLACE by default in some implementations, 
        # but here we want to explicitly prevent adding a patient if ID exists 
        # unless it's an update (which is handled by update_patient)
        if self.get_patient(patient.patient_id):
            print(f"[ERROR] add_patient: Patient ID {patient.patient_id} already exists")
            return False

        if self.db.save('patients', patient, 'patient_id'):
            try:
                name = f"{getattr(patient, 'last_name', '')} {getattr(patient, 'first_name', '')}".strip()
                self.add_activity(None, 'add', 'patient', patient.patient_id, name)
            except Exception:
                pass
            return True
        return False

    def get_patient(self, patient_id: str) -> Optional[Patient]:
        return self.db.get_by_id(Patient, 'patients', patient_id, 'patient_id')

    def get_patient_by_id(self, patient_id: str) -> Optional[Patient]:
        return self.get_patient(patient_id)

    def search_patients(self, search_term: str) -> List[Patient]:
        search_term = search_term.lower().strip()
        if not search_term:
            return self.patients
        return self.db.search(Patient, 'patients', search_term, ['first_name', 'last_name', 'patient_id'])

    def update_patient(self, original_id: str, **kwargs) -> bool:
        patient = self.get_patient(original_id)
        if not patient:
            return False

        new_id = kwargs.get('patient_id')
        if new_id and new_id != original_id:
            if self.get_patient(new_id):
                return False
            conn = self.db.get_connection()
            try:
                conn.execute("UPDATE appointments SET patient_id = ? WHERE patient_id = ?", (new_id, original_id))
                conn.execute("UPDATE medical_records SET patient_id = ? WHERE patient_id = ?", (new_id, original_id))
                conn.execute("UPDATE prescriptions SET patient_id = ? WHERE patient_id = ?", (new_id, original_id))
                conn.execute("UPDATE bills SET patient_id = ? WHERE patient_id = ?", (new_id, original_id))
                conn.execute("UPDATE lab_results SET patient_id = ? WHERE patient_id = ?", (new_id, original_id))
                conn.execute("UPDATE queue SET patient_id = ? WHERE patient_id = ?", (new_id, original_id))
                conn.commit()
            except Exception as e:
                print(f"Error updating related IDs: {e}")
                conn.rollback()
            finally:
                conn.close()
            
            # Delete old record since we are changing the primary key
            self.db.delete('patients', original_id, 'patient_id')
            
            if original_id in self.patient_files:
                self.patient_files[new_id] = self.patient_files.pop(original_id)
            if original_id in self.patient_scheme:
                self.patient_scheme[new_id] = self.patient_scheme.pop(original_id)

        for key, value in kwargs.items():
            if hasattr(patient, key):
                setattr(patient, key, value)

        return self.db.save('patients', patient, 'patient_id')

    def delete_patient(self, patient_id: str, permanent: bool = False) -> bool:
        if permanent:
            if self.db.delete('patients', patient_id, 'patient_id'):
                try:
                    self.add_activity(None, 'permanent_delete', 'patient', patient_id, f"Permanently deleted patient {patient_id}")
                except Exception:
                    pass
                return True
            return False
        
        # Soft delete
        patient = self.db.get_by_id(Patient, 'patients', patient_id, 'patient_id')
        if patient:
            patient.is_deleted = 1
            patient.deleted_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if self.db.save('patients', patient, 'patient_id'):
                try:
                    self.add_activity(None, 'delete', 'patient', patient_id, f"Soft-deleted patient {patient_id}")
                except Exception:
                    pass
                return True
        return False

    def delete_all_patients(self) -> bool:
        """Delete all patients and related records from the system."""
        tables_to_clear = [
            'appointments',
            'medical_records',
            'prescriptions',
            'bills',
            'lab_results',
            'queue',
            'patients'
        ]
        
        success = True
        for table in tables_to_clear:
            try:
                if not self.db.delete_all(table):
                    success = False
            except Exception as e:
                print(f"[ERROR] Failed to clear table {table}: {e}")
                success = False
        
        # Clear dictionaries
        self.patient_files = {}
        self.patient_scheme = {}
        
        # Clear caches
        self._patients_cache = []
        self._appointments_cache = []
        self._medical_records_cache = []
        self._prescriptions_cache = []
        self._bills_cache = []
        self._lab_results_cache = []
        self._queue_cache = []
        
        # Save changes to dictionaries
        self.save_data()
        
        try:
            self.add_activity(None, 'delete_all', 'patient', 'ALL', 'All patients and related records deleted')
        except Exception:
            pass
            
        return success

    # ---------- Doctors ----------
    def add_doctor(self, doctor: Doctor) -> bool:
        if self.db.save('doctors', doctor, 'doctor_id'):
            try:
                name = f"{getattr(doctor, 'first_name', '')} {getattr(doctor, 'last_name', '')}".strip()
                self.add_activity(None, 'add', 'doctor', doctor.doctor_id, name)
            except Exception:
                pass
            return True
        return False

    def get_doctor(self, doctor_id: str) -> Optional[Doctor]:
        return self.db.get_by_id(Doctor, 'doctors', doctor_id, 'doctor_id')

    def get_doctor_by_id(self, doctor_id: str) -> Optional[Doctor]:
        return self.get_doctor(doctor_id)

    def get_available_doctors(self) -> List[Doctor]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM doctors WHERE LOWER(status) = 'available'")
        rows = cursor.fetchall()
        conn.close()
        return [self.db._row_to_obj(Doctor, row) for row in rows]

    def search_doctors(self, search_term: str) -> List[Doctor]:
        search_term = search_term.lower().strip()
        if not search_term:
            return self.doctors
        return self.db.search(Doctor, 'doctors', search_term, ['first_name', 'last_name', 'doctor_id', 'specialty'])

    def update_doctor(self, doctor_id: str, **kwargs) -> bool:
        doctor = self.get_doctor(doctor_id)
        if not doctor:
            return False
        for key, value in kwargs.items():
            if hasattr(doctor, key):
                setattr(doctor, key, value)
        return self.db.save('doctors', doctor, 'doctor_id')

    def delete_doctor(self, doctor_id: str) -> bool:
        if self.db.delete('doctors', doctor_id, 'doctor_id'):
            try:
                self.add_activity(None, 'delete', 'doctor', doctor_id, '')
            except Exception:
                pass
            return True
        return False

    def delete_all_doctors_except(self, keep_id: str) -> bool:
        """Delete all doctors except the specified one."""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM doctors WHERE doctor_id != ?", (keep_id,))
            conn.commit()
            conn.close()
            
            # Clear cache
            self._doctors_cache = []
            
            # Add activity
            try:
                self.add_activity(None, 'delete_all_except', 'doctor', keep_id, f"Deleted all doctors except {keep_id}")
            except Exception:
                pass
                
            return True
        except Exception as e:
            print(f"[ERROR] Failed to delete doctors: {e}")
            return False

    # ---------- Appointments ----------
    def schedule_appointment(self, appointment: Appointment) -> bool:
        if self.db.save('appointments', appointment, 'appointment_id'):
            try:
                self.add_activity(None, 'schedule', 'appointment', appointment.appointment_id,
                                  f"{appointment.patient_id} -> {appointment.doctor_id} on {appointment.appointment_date} {appointment.appointment_time}")
            except Exception:
                pass
            return True
        return False

    def search_appointments(self, search_term: str) -> List[Appointment]:
        search_term = search_term.lower().strip()
        if not search_term:
            return self.appointments
        return self.db.search(Appointment, 'appointments', search_term,
                              ['appointment_id', 'patient_id', 'doctor_id', 'appointment_date', 'status'])

    def get_patient_appointments(self, patient_id: str) -> List[Appointment]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM appointments WHERE patient_id = ?", (patient_id,))
        rows = cursor.fetchall()
        conn.close()
        return [self.db._row_to_obj(Appointment, row) for row in rows]

    def get_doctor_appointments(self, doctor_id: str, date: str) -> List[Appointment]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM appointments WHERE doctor_id = ? AND appointment_date = ?", (doctor_id, date))
        rows = cursor.fetchall()
        conn.close()
        return [self.db._row_to_obj(Appointment, row) for row in rows]

    def update_appointment_status(self, appointment_id: str, status: str) -> bool:
        appointment = self.get_appointment(appointment_id)
        if appointment:
            appointment.status = status
            if self.db.save('appointments', appointment, 'appointment_id'):
                try:
                    self.add_activity(None, 'update_status', 'appointment', appointment_id, status)
                except Exception:
                    pass
                return True
        return False

    def get_appointment(self, appointment_id: str) -> Optional[Appointment]:
        return self.db.get_by_id(Appointment, 'appointments', appointment_id, 'appointment_id')

    def update_appointment(self, appointment_id: str, **kwargs) -> bool:
        appointment = self.get_appointment(appointment_id)
        if not appointment:
            return False
        for key, value in kwargs.items():
            if hasattr(appointment, key):
                setattr(appointment, key, value)
        return self.db.save('appointments', appointment, 'appointment_id')

    def delete_appointment(self, appointment_id: str) -> bool:
        if self.db.delete('appointments', appointment_id, 'appointment_id'):
            try:
                self.add_activity(None, 'delete', 'appointment', appointment_id, '')
            except Exception:
                pass
            return True
        return False

    # ---------- Medical Records ----------
    def add_medical_record(self, record: MedicalRecord) -> bool:
        if self.db.save('medical_records', record, 'record_id'):
            try:
                self.add_activity(None, 'add', 'medical_record', record.record_id, record.patient_id)
            except Exception:
                pass
            return True
        return False

    def get_patient_medical_records(self, patient_id: str) -> List[MedicalRecord]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medical_records WHERE patient_id = ?", (patient_id,))
        rows = cursor.fetchall()
        conn.close()
        return [self.db._row_to_obj(MedicalRecord, row) for row in rows]

    def get_medical_record(self, record_id: str) -> Optional[MedicalRecord]:
        return self.db.get_by_id(MedicalRecord, 'medical_records', record_id, 'record_id')

    def update_medical_record(self, record: MedicalRecord) -> bool:
        if self.db.save('medical_records', record, 'record_id'):
            try:
                self.add_activity(None, 'update', 'medical_record', record.record_id, record.patient_id)
            except Exception:
                pass
            return True
        return False

    # ---------- Prescriptions ----------
    def add_prescription(self, prescription: Prescription) -> bool:
        if self.db.save('prescriptions', prescription, 'prescription_id'):
            try:
                self.add_activity(None, 'add', 'prescription', prescription.prescription_id, prescription.patient_id)
            except Exception:
                pass
            return True
        return False

    def get_patient_prescriptions(self, patient_id: str) -> List[Prescription]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prescriptions WHERE patient_id = ?", (patient_id,))
        rows = cursor.fetchall()
        conn.close()
        return [self.db._row_to_obj(Prescription, row) for row in rows]

    def get_prescription(self, prescription_id: str) -> Optional[Prescription]:
        return self.db.get_by_id(Prescription, 'prescriptions', prescription_id, 'prescription_id')

    def update_prescription(self, prescription: Prescription) -> bool:
        if self.db.save('prescriptions', prescription, 'prescription_id'):
            try:
                self.add_activity(None, 'update', 'prescription', prescription.prescription_id, prescription.patient_id)
            except Exception:
                pass
            return True
        return False

    def delete_prescription(self, prescription_id: str) -> bool:
        if self.db.delete('prescriptions', prescription_id, 'prescription_id'):
            try:
                self.add_activity(None, 'delete', 'prescription', prescription_id, '')
            except Exception:
                pass
            return True
        return False

    def delete_medical_record(self, record_id: str) -> bool:
        if self.db.delete('medical_records', record_id, 'record_id'):
            try:
                self.add_activity(None, 'delete', 'medical_record', record_id, '')
            except Exception:
                pass
            return True
        return False

    # ---------- Lab Results ----------
    def add_lab_result(self, result: LabResult) -> bool:
        if self.db.save('lab_results', result, 'result_id'):
            try:
                self.add_activity(None, 'add', 'lab_result', result.result_id, result.patient_id)
            except Exception:
                pass
            return True
        return False

    def get_lab_result(self, result_id: str) -> Optional[LabResult]:
        return self.db.get_by_id(LabResult, 'lab_results', result_id, 'result_id')

    def update_lab_result(self, result: LabResult) -> bool:
        if self.db.save('lab_results', result, 'result_id'):
            try:
                self.add_activity(None, 'update', 'lab_result', result.result_id, result.patient_id)
            except Exception:
                pass
            return True
        return False

    def delete_lab_result(self, result_id: str) -> bool:
        if self.db.delete('lab_results', result_id, 'result_id'):
            try:
                self.add_activity(None, 'delete', 'lab_result', result_id, '')
            except Exception:
                pass
            return True
        return False

    # ---------- Billing ----------
    def create_bill(self, bill: Bill) -> bool:
        if self.db.save('bills', bill, 'bill_id'):
            try:
                self.add_activity(None, 'create', 'bill', bill.bill_id, bill.patient_id)
            except Exception:
                pass
            return True
        return False

    def get_patient_bills(self, patient_id: str) -> List[Bill]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bills WHERE patient_id = ?", (patient_id,))
        rows = cursor.fetchall()
        conn.close()
        return [self.db._row_to_obj(Bill, row) for row in rows]

    def update_bill_status(self, bill_id: str, status: str) -> bool:
        bill = self.get_bill(bill_id)
        if bill:
            bill.status = status
            if self.db.save('bills', bill, 'bill_id'):
                try:
                    self.add_activity(None, 'update_status', 'bill', bill_id, status)
                except Exception:
                    pass
                return True
        return False

    def get_bill(self, bill_id: str) -> Optional[Bill]:
        return self.db.get_by_id(Bill, 'bills', bill_id, 'bill_id')

    def update_bill(self, bill: Bill) -> bool:
        if self.db.save('bills', bill, 'bill_id'):
            try:
                self.add_activity(None, 'update', 'bill', bill.bill_id, bill.patient_id)
            except Exception:
                pass
            return True
        return False

    def delete_bill(self, bill_id: str) -> bool:
        if self.db.delete('bills', bill_id, 'bill_id'):
            try:
                self.add_activity(None, 'delete', 'bill', bill_id, '')
            except Exception:
                pass
            return True
        return False

    def search_inventory(self, search_term: str) -> List[InventoryItem]:
        search_term = search_term.lower().strip()
        if not search_term:
            return self.inventory
        return self.db.search(InventoryItem, 'inventory', search_term, ['name', 'category', 'item_id'])

    # ---------- Inventory ----------
    def add_inventory_item(self, item: InventoryItem) -> bool:
        if self.db.save('inventory', item, 'item_id'):
            try:
                self.add_activity(None, 'add', 'inventory', item.item_id, item.name)
            except Exception:
                pass
            return True
        return False

    def update_inventory_quantity(self, item_id: str, quantity: int) -> bool:
        item = self.get_inventory_item(item_id)
        if item:
            item.quantity = quantity
            if self.db.save('inventory', item, 'item_id'):
                try:
                    self.add_activity(None, 'update_qty', 'inventory', item_id, str(quantity))
                except Exception:
                    pass
                return True
        return False

    def get_low_stock_items(self) -> List[InventoryItem]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inventory WHERE quantity <= min_quantity")
        rows = cursor.fetchall()
        conn.close()
        return [self.db._row_to_obj(InventoryItem, row) for row in rows]

    def get_inventory_item(self, item_id: str) -> Optional[InventoryItem]:
        return self.db.get_by_id(InventoryItem, 'inventory', item_id, 'item_id')

    def update_inventory_item(self, item: InventoryItem) -> bool:
        if self.db.save('inventory', item, 'item_id'):
            try:
                self.add_activity(None, 'update', 'inventory', item.item_id, item.name)
            except Exception:
                pass
            return True
        return False

    def delete_inventory_item(self, item_id: str) -> bool:
        if self.db.delete('inventory', item_id, 'item_id'):
            try:
                self.add_activity(None, 'delete', 'inventory', item_id, '')
            except Exception:
                pass
            return True
        return False

    # ---------- Queue Management ----------
    def add_to_queue(self, queue_item: QueueItem) -> None:
        self.db.save('queue', queue_item, 'queue_id')

    def estimate_wait_time(self, department: str) -> str:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM queue WHERE department = ? AND status = 'Waiting'", (department,))
        waiting_count = cursor.fetchone()[0]
        conn.close()
        wait_mins = waiting_count * 15
        if wait_mins == 0:
            return "5 mins"
        return f"{wait_mins} mins"

    def call_patient(self, queue_id: str) -> bool:
        item = self.db.get_by_id(QueueItem, 'queue', queue_id, 'queue_id')
        if item:
            item.status = "Calling"
            item.last_called_time = datetime.datetime.now().strftime("%H:%M:%S")
            return self.db.save('queue', item, 'queue_id')
        return False

    def transfer_patient(self, queue_id: str, new_dept: str, new_doctor_id: str) -> bool:
        item = self.db.get_by_id(QueueItem, 'queue', queue_id, 'queue_id')
        if item:
            item.department = new_dept
            item.assigned_doctor_id = new_doctor_id
            item.estimated_wait = self.estimate_wait_time(new_dept)
            return self.db.save('queue', item, 'queue_id')
        return False

    def requeue_patient(self, queue_id: str) -> bool:
        item = self.db.get_by_id(QueueItem, 'queue', queue_id, 'queue_id')
        if item:
            item.status = "Waiting"
            item.requeued_count = getattr(item, 'requeued_count', 0) + 1
            return self.db.save('queue', item, 'queue_id')
        return False

    def update_queue_status(self, queue_id: str, status: str) -> bool:
        item = self.db.get_by_id(QueueItem, 'queue', queue_id, 'queue_id')
        if item:
            item.status = status
            return self.db.save('queue', item, 'queue_id')
        return False

    def remove_from_queue(self, queue_id: str) -> bool:
        return self.db.delete('queue', queue_id, 'queue_id')

    def get_unread_count(self, user_id: str, role: str) -> int:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM messages
            WHERE is_read = 0 AND (recipient_id = ? OR recipient_id = ? OR recipient_id = 'all')
        """, (user_id, role))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_stats(self) -> Dict[str, Any]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        stats = {}
        cursor.execute("SELECT COUNT(*) FROM patients")
        stats['total_patients'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM appointments")
        stats['total_appointments'] = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(amount) FROM bills WHERE status = 'Paid'")
        stats['total_revenue'] = cursor.fetchone()[0] or 0.0
        cursor.execute("SELECT status, COUNT(*) FROM appointments GROUP BY status")
        stats['appointment_statuses'] = dict(cursor.fetchall())
        conn.close()
        return stats

    def get_dashboard_stats(self, days: int = 90) -> Dict[str, Any]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        stats = {}
        cursor.execute("""
            SELECT created_date, COUNT(*) FROM patients
            WHERE created_date >= date('now', ?)
            GROUP BY created_date
        """, (f"-{days} days",))
        stats['registration_map'] = dict(cursor.fetchall())
        cursor.execute("""
            SELECT appointment_date, COUNT(*) FROM appointments
            WHERE appointment_date >= date('now', ?)
            GROUP BY appointment_date
        """, (f"-{days} days",))
        stats['appointment_map'] = dict(cursor.fetchall())
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) FROM appointments WHERE appointment_date = ?", (today,))
        stats['todays_appointments'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Scheduled'")
        stats['pending_appointments'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Completed'")
        stats['completed_appointments'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM doctors WHERE LOWER(status) = 'available'")
        stats['active_doctors'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM bills WHERE status = 'Pending'")
        stats['pending_bills'] = cursor.fetchone()[0]
        conn.close()
        return stats

    def get_recent_appointments(self, limit: int = 5) -> List[Appointment]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM appointments ORDER BY appointment_date DESC, appointment_time DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [self.db._row_to_obj(Appointment, row) for row in rows]

    def get_active_queue(self, limit: int = 50) -> List[QueueItem]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM queue WHERE status != 'Completed' ORDER BY check_in_time ASC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [self.db._row_to_obj(QueueItem, row) for row in rows]

    def get_recent_notifications(self, user_id: str, role: str, limit: int = 5) -> List[Message]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM messages
            WHERE sender_id = 'system' AND (recipient_id = ? OR recipient_id = ? OR recipient_id = 'all')
            ORDER BY timestamp DESC LIMIT ?
        """, (user_id, role, limit))
        rows = cursor.fetchall()
        conn.close()
        return [self.db._row_to_obj(Message, row) for row in rows]

    def get_messages_for_user(self, user_id: str, role: str, limit: int = 100) -> List[Message]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM messages
            WHERE recipient_id = ? OR recipient_id = ? OR recipient_id = 'all' OR sender_id = ?
            ORDER BY timestamp DESC LIMIT ?
        """, (user_id, role, user_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [self.db._row_to_obj(Message, row) for row in rows]

    def get_lab_records(self, limit: int = 100) -> List[MedicalRecord]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM medical_records
            WHERE LOWER(consult_reason) LIKE '%lab%' OR LOWER(consult_reason) LIKE '%blood%' OR LOWER(consult_reason) LIKE '%test%'
               OR LOWER(diagnosis) LIKE '%lab%' OR LOWER(diagnosis) LIKE '%blood%' OR LOWER(diagnosis) LIKE '%test%'
               OR LOWER(notes) LIKE '%lab%' OR LOWER(notes) LIKE '%blood%' OR LOWER(notes) LIKE '%test%'
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [self.db._row_to_obj(MedicalRecord, row) for row in rows]

    def get_report_stats(self) -> Dict[str, Any]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        stats = {}
        cursor.execute("SELECT COUNT(*) FROM patients")
        stats['total_patients'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM doctors")
        stats['total_doctors'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM appointments")
        stats['total_appointments'] = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(amount) FROM bills")
        stats['revenue'] = cursor.fetchone()[0] or 0.0
        cursor.execute("SELECT specialty, COUNT(*) FROM doctors GROUP BY specialty")
        stats['department_counts'] = dict(cursor.fetchall())
        cursor.execute("SELECT gender, COUNT(*) FROM patients GROUP BY gender")
        stats['gender_counts'] = dict(cursor.fetchall())
        cursor.execute("SELECT status, COUNT(*) FROM appointments GROUP BY status")
        stats['status_counts'] = dict(cursor.fetchall())
        conn.close()
        return stats

    def update_settings(self, **kwargs) -> None:
        self.settings.update(kwargs)
        try:
            if "supabase_project_id" in kwargs and kwargs.get("supabase_project_id"):
                os.environ["SUPABASE_PROJECT_ID"] = str(kwargs.get("supabase_project_id"))
            if "supabase_url" in kwargs and kwargs.get("supabase_url"):
                os.environ["SUPABASE_URL"] = str(kwargs.get("supabase_url"))
            if "supabase_api_key" in kwargs and kwargs.get("supabase_api_key"):
                os.environ["SUPABASE_API_KEY"] = str(kwargs.get("supabase_api_key"))
            if "supabase_service_role" in kwargs and kwargs.get("supabase_service_role"):
                os.environ["SUPABASE_SERVICE_ROLE"] = str(kwargs.get("supabase_service_role"))
            if "supabase_bucket" in kwargs and kwargs.get("supabase_bucket"):
                os.environ["SUPABASE_BUCKET"] = str(kwargs.get("supabase_bucket"))
            if "supabase_object_path" in kwargs and kwargs.get("supabase_object_path"):
                os.environ["SUPABASE_OBJECT_PATH"] = str(kwargs.get("supabase_object_path"))
        except Exception:
            pass
        self.save_data()

    def _hash_password(self, password: str, salt: Optional[str] = None) -> Dict[str, str]:
        if not salt:
            salt = uuid.uuid4().hex
        h = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
        return {'salt': salt, 'hash': h}

    def register_user(self, username: str, password: str, role: str = 'user', actor_role: Optional[str] = None) -> bool:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE LOWER(username) = LOWER(?)", (username,))
        exists = cursor.fetchone()[0] > 0

        r = (role or 'user').strip().lower()
        admin_roles = {'admin', 'admin doctor', 'admin_doctor'}
        if r in admin_roles:
            actor_is_admin = (actor_role or '').strip().lower() in admin_roles
            cursor.execute("SELECT COUNT(*) FROM users WHERE LOWER(role) IN ('admin', 'admin doctor', 'admin_doctor')")
            existing_admin = cursor.fetchone()[0] > 0
            if not actor_is_admin and existing_admin:
                conn.close()
                return False
        conn.close()

        if exists:
            return False

        creds = self._hash_password(password)
        user = User(
            user_id=self.generate_id('USR'),
            username=username,
            password_salt=creds['salt'],
            password_hash=creds['hash'],
            role=r,
            is_active=True,
            is_verified=False,
            otp_enabled=False
        )
        if self.db.save('users', user, 'user_id'):
            return True
        return False

    def authenticate(self, username: str, password: str) -> Optional[User]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        user = self.db._row_to_obj(User, row)
        creds = self._hash_password(password, user.password_salt)
        if creds['hash'] == user.password_hash and user.is_active:
            return user
        return None

    def add_message(self, message: Message) -> bool:
        return self.db.save('messages', message, 'message_id')

    def add_activity(self, actor: Optional[str], action: str, entity: str, entity_id: str, summary: str) -> None:
        entry = {
            'id': self.generate_id('ACT'),
            'actor': actor or 'system',
            'action': action,
            'entity': entity,
            'entity_id': entity_id,
            'summary': summary,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.activity.append(entry)
        if len(self.activity) > 500:
            self.activity = self.activity[-500:]
        # NOTE: do NOT call save_data() here — add_activity is called on every
        # DB write, so saving here caused O(N) disk writes per user action and
        # could interfere with data integrity. Activity is flushed on the next
        # explicit save_data() call (settings change, file upload, etc.).

    def update_user_role(self, target_username: str, new_role: str, actor_username: str) -> bool:
        admin_roles = {'admin', 'admin doctor', 'admin_doctor'}
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM users WHERE LOWER(username) = LOWER(?)", (actor_username,))
        row = cursor.fetchone()
        if not row or row[0].lower() not in admin_roles:
            conn.close()
            return False
        cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (target_username,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        user = self.db._row_to_obj(User, row)
        old_role = (user.role or '').strip().lower()
        user.role = (new_role or '').strip().lower()
        if self.db.save('users', user, 'user_id'):
            conn.close()
            try:
                self.add_activity(actor_username, 'update_role', 'user', user.user_id,
                                  f"{user.username}: {old_role} -> {user.role}")
            except Exception:
                pass
            return True
        conn.close()
        return False

    def toggle_user_status(self, target_username: str, active: bool, actor_username: str) -> bool:
        admin_roles = {'admin', 'admin doctor', 'admin_doctor'}
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM users WHERE LOWER(username) = LOWER(?)", (actor_username,))
        row = cursor.fetchone()
        if not row or row[0].lower() not in admin_roles:
            conn.close()
            return False
        cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (target_username,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        user = self.db._row_to_obj(User, row)
        user.is_active = active
        if self.db.save('users', user, 'user_id'):
            conn.close()
            self.add_activity(actor_username, 'toggle_status', 'user', user.user_id,
                              f"{user.username}: {'Active' if active else 'Inactive'}")
            return True
        conn.close()
        return False

    def toggle_user_verification(self, target_username: str, verified: bool, actor_username: str) -> bool:
        admin_roles = {'admin', 'admin doctor', 'admin_doctor'}
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM users WHERE LOWER(username) = LOWER(?)", (actor_username,))
        row = cursor.fetchone()
        if not row or row[0].lower() not in admin_roles:
            conn.close()
            return False
        cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (target_username,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        user = self.db._row_to_obj(User, row)
        user.is_verified = verified
        if self.db.save('users', user, 'user_id'):
            conn.close()
            self.add_activity(actor_username, 'toggle_verification', 'user', user.user_id,
                              f"{user.username}: {'Verified' if verified else 'Unverified'}")
            return True
        conn.close()
        return False

    def toggle_user_2fa(self, target_username: str, enabled: bool, actor_username: str) -> bool:
        admin_roles = {'admin', 'admin doctor', 'admin_doctor'}
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM users WHERE LOWER(username) = LOWER(?)", (actor_username,))
        row = cursor.fetchone()
        if not row or row[0].lower() not in admin_roles:
            conn.close()
            return False
        cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (target_username,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        user = self.db._row_to_obj(User, row)
        user.otp_enabled = enabled
        if not enabled:
            user.otp_secret = None
        if self.db.save('users', user, 'user_id'):
            conn.close()
            self.add_activity(actor_username, 'toggle_2fa', 'user', user.user_id,
                              f"{user.username}: {'2FA Enabled' if enabled else '2FA Disabled'}")
            return True
        conn.close()
        return False

    def _resolve_onedrive_base(self) -> Optional[str]:
        for env_key in ["OneDrive", "OneDriveCommercial", "OneDriveConsumer"]:
            p = os.environ.get(env_key)
            if p and os.path.isdir(p):
                return p
        userprofile = os.environ.get("UserProfile") or os.path.expanduser("~")
        try:
            for name in os.listdir(userprofile):
                if name.startswith("OneDrive"):
                    p = os.path.join(userprofile, name)
                    if os.path.isdir(p):
                        return p
        except Exception:
            pass
        return None

    def _route_data_file_to_onedrive(self, file_name: str) -> Optional[str]:
        base = self._resolve_onedrive_base()
        if not base:
            return None
        appdir = os.path.join(base, "Limbe Medical")
        try:
            os.makedirs(appdir, exist_ok=True)
        except Exception:
            return None
        return os.path.join(appdir, file_name)

    def _get_remote_json(self, path: str, base: str) -> Dict[str, Any]:
        url = base.rstrip('/') + path
        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))

    def _post_remote_json(self, path: str, payload: Dict[str, Any], base: str) -> None:
        url = base.rstrip('/') + path
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()


class HospitalHTTPHandler(BaseHTTPRequestHandler):
    hms: HospitalManagementSystem = None

    def _send_json(self, obj: Any, code: int = 200):
        body = json.dumps(obj).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith('/api/load'):
            data = {
                'patients': [asdict(p) for p in self.hms.patients[:100]],
                'doctors': [asdict(d) for d in self.hms.doctors],
                'appointments': [asdict(a) for a in self.hms.appointments[:100]],
                'medical_records': [asdict(m) for m in self.hms.medical_records[:100]],
                'prescriptions': [asdict(p) for p in self.hms.prescriptions[:100]],
                'bills': [asdict(b) for b in self.hms.bills[:100]],
                'inventory': [asdict(i) for i in self.hms.inventory[:100]],
                'users': [asdict(u) for u in self.hms.users[:100]],
                'settings': self.hms.settings,
                'activity': self.hms.activity
            }
            self._send_json(data)
            return
        if self.path.startswith('/api/activity'):
            self._send_json({'activity': self.hms.activity})
            return
        self._send_json({'error': 'not found'}, 404)

    def do_POST(self):
        if self.path.startswith('/api/save'):
            length = int(self.headers.get('Content-Length', '0') or '0')
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw.decode('utf-8'))
            except Exception:
                self._send_json({'error': 'invalid json'}, 400)
                return
            try:
                with open(self.hms.data_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                self.hms._apply_loaded_data(data)
            except Exception as e:
                self._send_json({'error': str(e)}, 500)
                return
            self._send_json({'ok': True})
            return
        self._send_json({'error': 'not found'}, 404)


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def start_http_server(host: str = '0.0.0.0', port: int = 8000) -> None:
    hms = HospitalManagementSystem()
    HospitalHTTPHandler.hms = hms
    server = ThreadingHTTPServer((host, port), HospitalHTTPHandler)
    print(f"Server running on http://{host}:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


# ==============================
# 🚀 ENTRY POINT
# ==============================

def main() -> HospitalManagementSystem:
    """Initialize and return the Hospital Management System."""
    hms = HospitalManagementSystem()
    print("=" * 60)
    print("LIMBE MEDICAL CLINIC - HOSPITAL MANAGEMENT SYSTEM")
    print("=" * 60)
    print(f"Loaded:")
    print(f"  Patients         : {hms.get_patients_count()}")
    print(f"  Doctors          : {hms.get_doctors_count()}")
    print(f"  Appointments     : {hms.get_appointments_count()}")
    print(f"  Medical Records  : {hms.get_medical_records_count()}")
    print(f"  Bills            : {hms.get_bills_count()}")
    print(f"  Inventory Items  : {hms.db.count('inventory')}")
    print("=" * 60)
    return hms


if __name__ == "__main__":
    main()