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
from supabase_data_manager import get_supabase_json, put_supabase_json

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


# ==============================
# 🏥 HOSPITAL MANAGEMENT SYSTEM
# ==============================

class HospitalManagementSystem:
    """Core class for managing hospital data and operations."""

    def __init__(self, data_file: str = "hospital_data.json"):
        self.data_file = data_file

        self.patients: List[Patient] = []
        self.doctors: List[Doctor] = []
        self.appointments: List[Appointment] = []
        self.medical_records: List[MedicalRecord] = []
        self.prescriptions: List[Prescription] = []
        self.bills: List[Bill] = []
        self.inventory: List[InventoryItem] = []
        self.users: List[User] = []
        self.messages: List[Message] = []
        self.queue: List[QueueItem] = []
        self.lab_results: List[LabResult] = []
        self.activity: List[Dict[str, Any]] = []
        self.patient_files: Dict[str, List[Dict[str, Any]]] = {}
        self.patient_scheme: Dict[str, Dict[str, Any]] = {}

        self.settings: Dict[str, Any] = {
            'theme': 'Light',
            'notifications': True,
            'auto_backup': False,
            'language': 'English',
            'date_format': 'DD/MM/YYYY',
            'server_url': None,
            'supabase_project_id': os.environ.get('SUPABASE_PROJECT_ID', 'qiudxdvssvkbpoovwpbr'),
            'supabase_url': os.environ.get('SUPABASE_URL', 'https://qiudxdvssvkbpoovwpbr.supabase.co'),
            # We use the service role key for API key fallback to ensure permissions, as the publishable key was causing issues.
            'supabase_api_key': os.environ.get('SUPABASE_API_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFpdWR4ZHZzc3ZrYnBvb3Z3cGJyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTUyOTQ2NywiZXhwIjoyMDgxMTA1NDY3fQ.WoHT4S5Or9sjs4TpB9gpq4ys5F9MlTNiToZA8dOfUPw'),
            'supabase_service_role': os.environ.get('SUPABASE_SERVICE_ROLE', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFpdWR4ZHZzc3ZrYnBvb3Z3cGJyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTUyOTQ2NywiZXhwIjoyMDgxMTA1NDY3fQ.WoHT4S5Or9sjs4TpB9gpq4ys5F9MlTNiToZA8dOfUPw'),
        }

        onedrive_path = self._route_data_file_to_onedrive(os.path.basename(self.data_file))
        if onedrive_path:
            if os.path.exists(self.data_file) and not os.path.exists(onedrive_path):
                try:
                    shutil.copy2(self.data_file, onedrive_path)
                except Exception:
                    pass
            self.data_file = onedrive_path

        self.load_data()

    # ---------- Utility ----------
    @staticmethod
    def generate_id(prefix: str) -> str:
        """Generate a unique ID with a prefix."""
        return f"{prefix}{str(uuid.uuid4())[:8]}"

    # ---------- Persistence ----------
    def save_data(self) -> None:
        """Save all data to a single JSON file."""
        try:
            data = {
                'patients': [asdict(p) for p in self.patients],
                'doctors': [asdict(d) for d in self.doctors],
                'appointments': [asdict(a) for a in self.appointments],
                'medical_records': [asdict(m) for m in self.medical_records],
                'prescriptions': [asdict(p) for p in self.prescriptions],
                'bills': [asdict(b) for b in self.bills],
                'inventory': [asdict(i) for i in self.inventory],
                'users': [asdict(u) for u in self.users],
                'messages': [asdict(m) for m in self.messages],
                'queue': [asdict(q) for q in self.queue],
                'lab_results': [asdict(lr) for lr in self.lab_results],
                'settings': self.settings,
                'activity': self.activity,
                'patient_files': self.patient_files,
                'patient_scheme': self.patient_scheme
            }
            srv = self.settings.get('server_url')
            if srv:
                try:
                    self._post_remote_json('/api/save', data, srv)
                except Exception as e:
                    print(f"[WARN] Remote save failed: {e}")
            try:
                from supabase_data_manager import supabase_connected, put_supabase_json
                if supabase_connected():
                    put_supabase_json(data)
            except Exception as e:
                print(f"[WARN] Supabase save failed: {e}")

            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def load_data(self) -> None:
        """Load all data from the JSON file."""
        try:
            from supabase_data_manager import get_supabase_json
            data = get_supabase_json()
            if data:
                self._apply_loaded_data(data)
                return
        except Exception as e:
            print(f"[WARN] Supabase load failed: {e}")

        if not os.path.exists(self.data_file):
            print(f"[ERROR] Data file '{self.data_file}' not found and no remote data available.")
            # We do NOT create a fresh file automatically anymore per user request.
            # But we might need empty structures to avoid crashes if the app continues running.
            # Ideally, we should probably raise an error or exit, but for safety in a running app,
            # we'll just leave lists empty (initialized in __init__) and let the user know.
            return

        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._apply_loaded_data(data)
        except Exception as e:
            print(f"[ERROR] Failed to load data from {self.data_file}: {e}")

    def _apply_loaded_data(self, data: Dict[str, Any]) -> None:
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

        self.patients = [Patient(**_filter(Patient, p)) for p in data.get('patients', [])]
        self.doctors = [Doctor(**_filter(Doctor, d)) for d in data.get('doctors', [])]
        self.appointments = [Appointment(**_normalize_appointment(a)) for a in data.get('appointments', [])]
        self.medical_records = [MedicalRecord(**_normalize_record(m)) for m in data.get('medical_records', [])]
        self.prescriptions = [Prescription(**_filter(Prescription, p)) for p in data.get('prescriptions', [])]
        self.bills = [Bill(**_normalize_bill(b)) for b in data.get('bills', [])]
        self.inventory = [InventoryItem(**_filter(InventoryItem, i)) for i in data.get('inventory', [])]
        self.users = [User(**_filter(User, u)) for u in data.get('users', [])]
        self.messages = [Message(**_filter(Message, m)) for m in data.get('messages', [])]
        self.queue = [QueueItem(**_filter(QueueItem, q)) for q in data.get('queue', [])]
        self.lab_results = [LabResult(**_filter(LabResult, lr)) for lr in data.get('lab_results', [])]
        self.departments = data.get('departments', [])
        self.settings = data.get('settings', self.settings)
        self.activity = data.get('activity', [])
        self.patient_files = data.get('patient_files', {})
        self.patient_scheme = data.get('patient_scheme', {})

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
                shutil.copy2(src, dest)
                rel_path = os.path.relpath(dest, base_dir)
                sup_id = ''
                # Placeholder: local copy made; integrate Supabase Storage upload when configured
                entries.append({
                    'file_name': name,
                    'path': rel_path,
                    'uploaded_at': ts,
                    'source_appointment_id': source_appointment_id or '',
                    'source_record_id': source_record_id or '',
                    'supabase_file_id': sup_id
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
        new_entries = [e for e in entries if e.get('path') != rel_path]
        if len(new_entries) == len(entries):
            return False
        try:
            if os.path.exists(abs_path):
                os.remove(abs_path)
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
            _, old_ext = os.path.splitext(entry.get('file_name',''))
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
            self.add_activity(None, 'update_scheme', 'patient', patient_id, scheme_info.get('scheme_name',''))
        except Exception:
            pass
        return True

    def get_patient_scheme(self, patient_id: str) -> Dict[str, Any]:
        return self.patient_scheme.get(patient_id, {})

    # ---------- Patients ----------
    def add_patient(self, patient: Patient) -> bool:
        self.patients.append(patient)
        self.save_data()
        try:
            name = f"{getattr(patient,'first_name','')} {getattr(patient,'last_name','')}".strip()
            self.add_activity(None, 'add', 'patient', patient.patient_id, name)
        except Exception:
            pass
        return True

    def get_patient(self, patient_id: str) -> Optional[Patient]:
        return next((p for p in self.patients if p.patient_id == patient_id), None)

    def get_patient_by_id(self, patient_id: str) -> Optional[Patient]:
        return self.get_patient(patient_id)

    def search_patients(self, search_term: str) -> List[Patient]:
        search_term = search_term.lower()
        return [
            p for p in self.patients
            if search_term in p.first_name.lower()
            or search_term in p.last_name.lower()
            or search_term in p.patient_id.lower()
        ]

    def update_patient(self, patient_id: str, **kwargs) -> bool:
        patient = self.get_patient(patient_id)
        if not patient:
            return False
        for key, value in kwargs.items():
            if hasattr(patient, key):
                setattr(patient, key, value)
        self.save_data()
        return True

    def delete_patient(self, patient_id: str) -> bool:
        for i, p in enumerate(self.patients):
            if p.patient_id == patient_id:
                del self.patients[i]
                self.save_data()
                try:
                    self.add_activity(None, 'delete', 'patient', patient_id, '')
                except Exception:
                    pass
                return True
        return False

    # ---------- Doctors ----------
    def add_doctor(self, doctor: Doctor) -> bool:
        self.doctors.append(doctor)
        self.save_data()
        try:
            name = f"{getattr(doctor,'first_name','')} {getattr(doctor,'last_name','')}".strip()
            self.add_activity(None, 'add', 'doctor', doctor.doctor_id, name)
        except Exception:
            pass
        return True

    def get_doctor(self, doctor_id: str) -> Optional[Doctor]:
        return next((d for d in self.doctors if d.doctor_id == doctor_id), None)

    def get_doctor_by_id(self, doctor_id: str) -> Optional[Doctor]:
        return self.get_doctor(doctor_id)

    def get_available_doctors(self) -> List[Doctor]:
        return [d for d in self.doctors if d.status.lower() == "available"]

    def search_doctors(self, search_term: str) -> List[Doctor]:
        search_term = search_term.lower()
        return [
            d for d in self.doctors
            if search_term in d.first_name.lower()
            or search_term in d.last_name.lower()
            or search_term in d.doctor_id.lower()
            or search_term in d.specialty.lower()
        ]

    def update_doctor(self, doctor_id: str, **kwargs) -> bool:
        doctor = self.get_doctor(doctor_id)
        if not doctor:
            return False
        for key, value in kwargs.items():
            if hasattr(doctor, key):
                setattr(doctor, key, value)
        self.save_data()
        return True

    def delete_doctor(self, doctor_id: str) -> bool:
        for i, d in enumerate(self.doctors):
            if d.doctor_id == doctor_id:
                del self.doctors[i]
                self.save_data()
                try:
                    self.add_activity(None, 'delete', 'doctor', doctor_id, '')
                except Exception:
                    pass
                return True
        return False

    # ---------- Appointments ----------
    def schedule_appointment(self, appointment: Appointment) -> bool:
        self.appointments.append(appointment)
        self.save_data()
        try:
            self.add_activity(None, 'schedule', 'appointment', appointment.appointment_id, f"{appointment.patient_id} -> {appointment.doctor_id} on {appointment.appointment_date} {appointment.appointment_time}")
        except Exception:
            pass
        return True

    def search_appointments(self, search_term: str) -> List[Appointment]:
        search_term = search_term.lower()
        return [
            a for a in self.appointments
            if search_term in a.appointment_id.lower()
            or search_term in a.patient_id.lower()
            or search_term in a.doctor_id.lower()
            or search_term in a.appointment_date.lower()
            or search_term in a.status.lower()
        ]

    def get_patient_appointments(self, patient_id: str) -> List[Appointment]:
        return [a for a in self.appointments if a.patient_id == patient_id]

    def get_doctor_appointments(self, doctor_id: str, date: str) -> List[Appointment]:
        return [a for a in self.appointments if a.doctor_id == doctor_id and a.appointment_date == date]

    def update_appointment_status(self, appointment_id: str, status: str) -> bool:
        for a in self.appointments:
            if a.appointment_id == appointment_id:
                a.status = status
                self.save_data()
                try:
                    self.add_activity(None, 'update_status', 'appointment', appointment_id, status)
                except Exception:
                    pass
                return True
        return False

    def get_appointment(self, appointment_id: str) -> Optional[Appointment]:
        return next((a for a in self.appointments if a.appointment_id == appointment_id), None)

    def update_appointment(self, appointment_id: str, **kwargs) -> bool:
        appointment = self.get_appointment(appointment_id)
        if not appointment:
            return False
        for key, value in kwargs.items():
            if hasattr(appointment, key):
                setattr(appointment, key, value)
        self.save_data()
        return True

    def delete_appointment(self, appointment_id: str) -> bool:
        for i, a in enumerate(self.appointments):
            if a.appointment_id == appointment_id:
                del self.appointments[i]
                self.save_data()
                try:
                    self.add_activity(None, 'delete', 'appointment', appointment_id, '')
                except Exception:
                    pass
                return True
        return False

    # ---------- Medical Records ----------
    def add_medical_record(self, record: MedicalRecord) -> bool:
        self.medical_records.append(record)
        self.save_data()
        try:
            self.add_activity(None, 'add', 'medical_record', record.record_id, record.patient_id)
        except Exception:
            pass
        return True

    def get_patient_medical_records(self, patient_id: str) -> List[MedicalRecord]:
        return [r for r in self.medical_records if r.patient_id == patient_id]

    def get_medical_record(self, record_id: str) -> Optional[MedicalRecord]:
        return next((r for r in self.medical_records if r.record_id == record_id), None)

    def update_medical_record(self, record: MedicalRecord) -> bool:
        for i, r in enumerate(self.medical_records):
            if r.record_id == record.record_id:
                self.medical_records[i] = record
                self.save_data()
                try:
                    self.add_activity(None, 'update', 'medical_record', record.record_id, record.patient_id)
                except Exception:
                    pass
                return True
        return False

    # ---------- Prescriptions ----------
    def add_prescription(self, prescription: Prescription) -> bool:
        self.prescriptions.append(prescription)
        self.save_data()
        try:
            self.add_activity(None, 'add', 'prescription', prescription.prescription_id, prescription.patient_id)
        except Exception:
            pass
        return True

    def get_patient_prescriptions(self, patient_id: str) -> List[Prescription]:
        return [p for p in self.prescriptions if p.patient_id == patient_id]

    def get_prescription(self, prescription_id: str) -> Optional[Prescription]:
        return next((p for p in self.prescriptions if p.prescription_id == prescription_id), None)

    def update_prescription(self, prescription: Prescription) -> bool:
        for i, p in enumerate(self.prescriptions):
            if p.prescription_id == prescription.prescription_id:
                self.prescriptions[i] = prescription
                self.save_data()
                try:
                    self.add_activity(None, 'update', 'prescription', prescription.prescription_id, prescription.patient_id)
                except Exception:
                    pass
                return True
        return False

    def delete_prescription(self, prescription_id: str) -> bool:
        for i, p in enumerate(self.prescriptions):
            if p.prescription_id == prescription_id:
                del self.prescriptions[i]
                self.save_data()
                try:
                    self.add_activity(None, 'delete', 'prescription', prescription_id, '')
                except Exception:
                    pass
                return True
        return False

    def delete_medical_record(self, record_id: str) -> bool:
        for i, r in enumerate(self.medical_records):
            if r.record_id == record_id:
                del self.medical_records[i]
                self.save_data()
                try:
                    self.add_activity(None, 'delete', 'medical_record', record_id, '')
                except Exception:
                    pass
                return True
        return False

    # ---------- Lab Results ----------
    def add_lab_result(self, result: LabResult) -> bool:
        self.lab_results.append(result)
        self.save_data()
        try:
            self.add_activity(None, 'add', 'lab_result', result.result_id, result.patient_id)
        except Exception:
            pass
        return True

    def get_lab_result(self, result_id: str) -> Optional[LabResult]:
        return next((r for r in self.lab_results if r.result_id == result_id), None)

    def update_lab_result(self, result: LabResult) -> bool:
        for i, r in enumerate(self.lab_results):
            if r.result_id == result.result_id:
                self.lab_results[i] = result
                self.save_data()
                try:
                    self.add_activity(None, 'update', 'lab_result', result.result_id, result.patient_id)
                except Exception:
                    pass
                return True
        return False

    def delete_lab_result(self, result_id: str) -> bool:
        for i, r in enumerate(self.lab_results):
            if r.result_id == result_id:
                del self.lab_results[i]
                self.save_data()
                try:
                    self.add_activity(None, 'delete', 'lab_result', result_id, '')
                except Exception:
                    pass
                return True
        return False

    # ---------- Billing ----------
    def create_bill(self, bill: Bill) -> bool:
        self.bills.append(bill)
        self.save_data()
        try:
            self.add_activity(None, 'create', 'bill', bill.bill_id, bill.patient_id)
        except Exception:
            pass
        return True

    def get_patient_bills(self, patient_id: str) -> List[Bill]:
        return [b for b in self.bills if b.patient_id == patient_id]

    def update_bill_status(self, bill_id: str, status: str) -> bool:
        for b in self.bills:
            if b.bill_id == bill_id:
                b.status = status
                self.save_data()
                try:
                    self.add_activity(None, 'update_status', 'bill', bill_id, status)
                except Exception:
                    pass
                return True
        return False

    def get_bill(self, bill_id: str) -> Optional[Bill]:
        return next((b for b in self.bills if b.bill_id == bill_id), None)

    def update_bill(self, bill: Bill) -> bool:
        for i, b in enumerate(self.bills):
            if b.bill_id == bill.bill_id:
                self.bills[i] = bill
                self.save_data()
                try:
                    self.add_activity(None, 'update', 'bill', bill.bill_id, bill.patient_id)
                except Exception:
                    pass
                return True
        return False

    def delete_bill(self, bill_id: str) -> bool:
        for i, b in enumerate(self.bills):
            if b.bill_id == bill_id:
                del self.bills[i]
                self.save_data()
                try:
                    self.add_activity(None, 'delete', 'bill', bill_id, '')
                except Exception:
                    pass
                return True
        return False

    # ---------- Inventory ----------
    def add_inventory_item(self, item: InventoryItem) -> bool:
        self.inventory.append(item)
        self.save_data()
        try:
            self.add_activity(None, 'add', 'inventory', item.item_id, item.name)
        except Exception:
            pass
        return True

    def update_inventory_quantity(self, item_id: str, quantity: int) -> bool:
        for i in self.inventory:
            if i.item_id == item_id:
                i.quantity = quantity
                self.save_data()
                try:
                    self.add_activity(None, 'update_qty', 'inventory', item_id, str(quantity))
                except Exception:
                    pass
                return True
        return False

    def get_low_stock_items(self) -> List[InventoryItem]:
        return [i for i in self.inventory if i.quantity <= i.min_quantity]

    def get_inventory_item(self, item_id: str) -> Optional[InventoryItem]:
        return next((i for i in self.inventory if i.item_id == item_id), None)

    def update_inventory_item(self, item: InventoryItem) -> bool:
        for idx, existing in enumerate(self.inventory):
            if existing.item_id == item.item_id:
                self.inventory[idx] = item
                self.save_data()
                try:
                    self.add_activity(None, 'update', 'inventory', item.item_id, item.name)
                except Exception:
                    pass
                return True
        return False

    def delete_inventory_item(self, item_id: str) -> bool:
        for idx, existing in enumerate(self.inventory):
            if existing.item_id == item_id:
                del self.inventory[idx]
                self.save_data()
                try:
                    self.add_activity(None, 'delete', 'inventory', item_id, '')
                except Exception:
                    pass
                return True
        return False

    # ---------- Queue Management ----------
    def add_to_queue(self, queue_item: QueueItem) -> None:
        """Add a patient to the queue."""
        self.queue.append(queue_item)
        self.save_data()

    def estimate_wait_time(self, department: str) -> str:
        """Estimate the wait time for a patient based on the number of waiting patients in a department."""
        # Simple estimation: 15 mins per waiting patient
        waiting_count = len([q for q in self.queue if q.department == department and q.status == 'Waiting'])
        wait_mins = waiting_count * 15
        if wait_mins == 0:
            return "5 mins"
        return f"{wait_mins} mins"

    def call_patient(self, queue_id: str) -> bool:
        """Mark a patient as being called."""
        for item in self.queue:
            if item.queue_id == queue_id:
                item.status = "Calling"
                item.last_called_time = datetime.datetime.now().strftime("%H:%M:%S")
                self.save_data()
                return True
        return False

    def transfer_patient(self, queue_id: str, new_dept: str, new_doctor_id: str) -> bool:
        """Transfer a patient to a different department or doctor."""
        for item in self.queue:
            if item.queue_id == queue_id:
                item.department = new_dept
                item.assigned_doctor_id = new_doctor_id
                # Reset estimated wait for the new department
                item.estimated_wait = self.estimate_wait_time(new_dept)
                self.save_data()
                return True
        return False

    def requeue_patient(self, queue_id: str) -> bool:
        """Re-queue a patient who might have been missed or needs a follow-up."""
        for item in self.queue:
            if item.queue_id == queue_id:
                item.status = "Waiting"
                item.requeued_count = getattr(item, 'requeued_count', 0) + 1
                self.save_data()
                return True
        return False

    def update_queue_status(self, queue_id: str, status: str) -> bool:
        """Update the status of a queue item."""
        for item in self.queue:
            if item.queue_id == queue_id:
                item.status = status
                self.save_data()
                return True
        return False

    def remove_from_queue(self, queue_id: str) -> bool:
        """Remove a patient from the queue."""
        initial_len = len(self.queue)
        self.queue = [item for item in self.queue if item.queue_id != queue_id]
        if len(self.queue) < initial_len:
            self.save_data()
            return True
        return False

    def get_queue(self) -> List[QueueItem]:
        """Get the current queue."""
        return self.queue

    def update_settings(self, **kwargs) -> None:
        self.settings.update(kwargs)
        # Sync critical Nhost settings into environment so data manager sees updates immediately
        try:
            # Supabase env sync
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
        if any(u.username.lower() == username.lower() for u in self.users):
            return False
        r = (role or 'user').strip().lower()
        admin_roles = {'admin', 'admin doctor', 'admin_doctor'}
        if r in admin_roles:
            actor_is_admin = (actor_role or '').strip().lower() in admin_roles
            existing_admin = any((u.role or '').strip().lower() in admin_roles for u in self.users)
            if not actor_is_admin and existing_admin:
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
        self.users.append(user)
        self.save_data()
        return True

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = next((u for u in self.users if u.username.lower() == username.lower()), None)
        if not user:
            return None
        creds = self._hash_password(password, user.password_salt)
        if creds['hash'] == user.password_hash:
            return user
        return None

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
        # Keep only last 500 entries
        self.activity.append(entry)
        if len(self.activity) > 500:
            self.activity = self.activity[-500:]
        self.save_data()

    def update_user_role(self, target_username: str, new_role: str, actor_username: str) -> bool:
        admin_roles = {'admin', 'admin doctor', 'admin_doctor'}
        actor = next((u for u in self.users if u.username.lower() == actor_username.lower()), None)
        if not actor or (actor.role or '').strip().lower() not in admin_roles:
            return False
        user = next((u for u in self.users if u.username.lower() == target_username.lower()), None)
        if not user:
            return False
        old_role = (user.role or '').strip().lower()
        user.role = (new_role or '').strip().lower()
        self.save_data()
        try:
            self.add_activity(actor_username, 'update_role', 'user', user.user_id, f"{user.username}: {old_role} -> {user.role}")
        except Exception:
            pass
        return True

    def toggle_user_status(self, target_username: str, active: bool, actor_username: str) -> bool:
        admin_roles = {'admin', 'admin doctor', 'admin_doctor'}
        actor = next((u for u in self.users if u.username.lower() == actor_username.lower()), None)
        if not actor or (actor.role or '').strip().lower() not in admin_roles:
            return False
        user = next((u for u in self.users if u.username.lower() == target_username.lower()), None)
        if not user:
            return False
        user.is_active = active
        self.save_data()
        self.add_activity(actor_username, 'toggle_status', 'user', user.user_id, f"{user.username}: {'Active' if active else 'Inactive'}")
        return True

    def toggle_user_verification(self, target_username: str, verified: bool, actor_username: str) -> bool:
        admin_roles = {'admin', 'admin doctor', 'admin_doctor'}
        actor = next((u for u in self.users if u.username.lower() == actor_username.lower()), None)
        if not actor or (actor.role or '').strip().lower() not in admin_roles:
            return False
        user = next((u for u in self.users if u.username.lower() == target_username.lower()), None)
        if not user:
            return False
        user.is_verified = verified
        self.save_data()
        self.add_activity(actor_username, 'toggle_verification', 'user', user.user_id, f"{user.username}: {'Verified' if verified else 'Unverified'}")
        return True

    def toggle_user_2fa(self, target_username: str, enabled: bool, actor_username: str) -> bool:
        admin_roles = {'admin', 'admin doctor', 'admin_doctor'}
        actor = next((u for u in self.users if u.username.lower() == actor_username.lower()), None)
        if not actor or (actor.role or '').strip().lower() not in admin_roles:
            return False
        user = next((u for u in self.users if u.username.lower() == target_username.lower()), None)
        if not user:
            return False
        user.otp_enabled = enabled
        if not enabled:
            user.otp_secret = None
        self.save_data()
        self.add_activity(actor_username, 'toggle_2fa', 'user', user.user_id, f"{user.username}: {'2FA Enabled' if enabled else '2FA Disabled'}")
        return True

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
                'patients': [asdict(p) for p in self.hms.patients],
                'doctors': [asdict(d) for d in self.hms.doctors],
                'appointments': [asdict(a) for a in self.hms.appointments],
                'medical_records': [asdict(m) for m in self.hms.medical_records],
                'prescriptions': [asdict(p) for p in self.hms.prescriptions],
                'bills': [asdict(b) for b in self.hms.bills],
                'inventory': [asdict(i) for i in self.hms.inventory],
                'users': [asdict(u) for u in self.hms.users],
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

    # ---------- GUI Hooks ----------
    def show_doctors(self):
        from gui_doctors import show_doctors_tab
        self.clear_content()
        show_doctors_tab(self.content_frame).pack(fill="both", expand=True)

    def show_reports(self):
        from gui_reports import show_reports_tab
        self.clear_content()
        show_reports_tab(self.content_frame).pack(fill="both", expand=True)

    def show_settings(self):
        from gui_settings import show_settings_tab
        self.clear_content()
        show_settings_tab(self.content_frame).pack(fill="both", expand=True)

    # ---------- Utility for GUI ----------
    def clear_content(self):
        """Clear all widgets from the main content frame (used by GUI)."""
        if hasattr(self, "content_frame"):
            for widget in self.content_frame.winfo_children():
                widget.destroy()


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
    print(f"  Patients: {len(hms.patients)}")
    print(f"  Doctors: {len(hms.doctors)}")
    print(f"  Appointments: {len(hms.appointments)}")
    print(f"  Medical Records: {len(hms.medical_records)}")
    print(f"  Bills: {len(hms.bills)}")
    print(f"  Inventory Items: {len(hms.inventory)}")
    print("=" * 60)
    return hms


if __name__ == "__main__":
    main()
