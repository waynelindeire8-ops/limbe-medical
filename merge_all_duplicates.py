import sys
import os
import re
from collections import defaultdict
import sqlite3

# Add current directory to path
sys.path.append(os.path.abspath('c:/Users/user/limbe-medical'))

from main import HospitalManagementSystem
from models import Patient, Appointment, MedicalRecord, Prescription, Bill, LabResult, QueueItem

def normalize_name(name):
    if not name:
        return ""
    # Lowercase, keep only lowercase letters
    return re.sub(r'[^a-z]', '', name.lower())

def get_normalized_id(pid):
    if not pid:
        return ""
    return re.sub(r'[^a-z0-9]', '', pid.lower())

def are_ids_similar(id1, id2):
    c1 = get_normalized_id(id1)
    c2 = get_normalized_id(id2)
    if c1 == c2:
        return True
    
    # Check if they share a prefix of at least 8 characters
    common_prefix_len = 0
    min_len = min(len(c1), len(c2))
    for k in range(min_len):
        if c1[k] == c2[k]:
            common_prefix_len += 1
        else:
            break
            
    return common_prefix_len >= 8

def evaluate_patient_record(p, counts):
    """Calculate a score for the patient record to determine the best master."""
    score = 0
    
    # Score for filled fields
    fields_to_check = [
        'date_of_birth', 'gender', 'phone', 'email', 'address', 
        'emergency_contact', 'blood_group', 'medical_history', 
        'scheme_provider', 'scheme_type'
    ]
    for field in fields_to_check:
        val = getattr(p, field, None)
        if val and str(val).strip() and str(val).strip().lower() not in ('none', 'null', 'n/a', ''):
            score += 1
            
    # Score for clinical records (we prefer records that already have history)
    total_records = sum(counts.values())
    score += total_records * 5
    
    # Tie breaker: prefer ID without hyphens or special chars, and matching length 11
    pid = p.patient_id
    if '-' not in pid and ' ' not in pid:
        score += 0.5
    if len(pid) == 11 and pid.isdigit():
        score += 0.5
        
    return score

def find_duplicate_groups(hms):
    patients = hms.patients
    print(f"Loaded {len(patients)} active patients.")
    
    # Group by normalized name
    name_groups = defaultdict(list)
    for p in patients:
        name_key = (normalize_name(p.first_name), normalize_name(p.last_name))
        name_groups[name_key].append(p)
        
    duplicate_groups = []
    
    for name_key, group in name_groups.items():
        if len(group) > 1:
            # Check if any pair in the group has similar IDs
            similar_ids = False
            for i in range(len(group)):
                for j in range(i+1, len(group)):
                    if are_ids_similar(group[i].patient_id, group[j].patient_id):
                        similar_ids = True
                        break
                if similar_ids:
                    break
            
            if similar_ids:
                # Retrieve counts for each
                members_with_counts = []
                for p in group:
                    pid = p.patient_id
                    counts = {
                        'appointments': hms.db.count('appointments', "patient_id = ?", (pid,)),
                        'medical_records': hms.db.count('medical_records', "patient_id = ?", (pid,)),
                        'prescriptions': hms.db.count('prescriptions', "patient_id = ?", (pid,)),
                        'bills': hms.db.count('bills', "patient_id = ?", (pid,)),
                        'lab_results': hms.db.count('lab_results', "patient_id = ?", (pid,)),
                        'queue': hms.db.count('queue', "patient_id = ?", (pid,))
                    }
                    members_with_counts.append((p, counts))
                duplicate_groups.append((name_key, members_with_counts))
                
    return duplicate_groups

def merge_patient_fields(master, dup):
    """Merge duplicate fields into master."""
    fields_to_check = [
        'date_of_birth', 'gender', 'phone', 'email', 'address', 
        'emergency_contact', 'blood_group', 'scheme_provider', 'scheme_type'
    ]
    
    modified = False
    for field in fields_to_check:
        master_val = getattr(master, field, None)
        dup_val = getattr(dup, field, None)
        
        # If master field is empty and duplicate field is not, fill it
        master_empty = not master_val or str(master_val).strip().lower() in ('none', 'null', 'n/a', '')
        dup_filled = dup_val and str(dup_val).strip() and str(dup_val).strip().lower() not in ('none', 'null', 'n/a', '')
        
        if master_empty and dup_filled:
            setattr(master, field, dup_val)
            modified = True
            
    # Special handle for medical history (concatenate if both have data)
    master_hist = getattr(master, 'medical_history', '')
    dup_hist = getattr(dup, 'medical_history', '')
    master_hist_empty = not master_hist or str(master_hist).strip().lower() in ('none', 'null', 'n/a', '')
    dup_hist_filled = dup_hist and str(dup_hist).strip() and str(dup_hist).strip().lower() not in ('none', 'null', 'n/a', '')
    
    if dup_hist_filled:
        if master_hist_empty:
            master.medical_history = dup_hist
            modified = True
        elif dup_hist not in master_hist:
            master.medical_history = f"{master_hist}; {dup_hist}"
            modified = True
            
    return modified

def execute_merge(dry_run=True):
    hms = HospitalManagementSystem()
    groups = find_duplicate_groups(hms)
    
    print(f"\nFound {len(groups)} duplicate patient groups to merge.")
    if dry_run:
        print("=== DRY RUN MODE: No database changes will be committed ===")
        
    successful_merges = 0
    total_clinical_records_moved = 0
    
    table_models = {
        'appointments': (Appointment, 'appointment_id'),
        'medical_records': (MedicalRecord, 'record_id'),
        'prescriptions': (Prescription, 'prescription_id'),
        'bills': (Bill, 'bill_id'),
        'lab_results': (LabResult, 'result_id'),
        'queue': (QueueItem, 'queue_id')
    }
    
    for name_key, members in groups:
        # Calculate scores to find the best master
        scored_members = []
        for p, counts in members:
            score = evaluate_patient_record(p, counts)
            scored_members.append((score, p, counts))
            
        # Sort by score descending
        scored_members.sort(key=lambda x: x[0], reverse=True)
        
        master_score, master, master_counts = scored_members[0]
        duplicates_to_merge = scored_members[1:]
        
        print(f"\nGroup: {master.first_name} {master.last_name}")
        print(f" -> Selected Master: ID={master.patient_id} | Score={master_score} | Phone={master.phone} | Scheme={master.scheme_provider} ({master.scheme_type})")
        
        for score, dup, counts in duplicates_to_merge:
            print(f" -> Duplicate to Merge: ID={dup.patient_id} | Score={score} | Phone={dup.phone} | Counts={counts}")
            
        if dry_run:
            # Just show what field merges would happen
            temp_master = Patient(**{f.name: getattr(master, f.name) for f in Patient.__dataclass_fields__.values()})
            for _, dup, _ in duplicates_to_merge:
                merge_patient_fields(temp_master, dup)
            # Show changed fields
            changed_fields = []
            for f in Patient.__dataclass_fields__.values():
                old_val = getattr(master, f.name)
                new_val = getattr(temp_master, f.name)
                if old_val != new_val:
                    changed_fields.append(f"{f.name}: '{old_val}' -> '{new_val}'")
            if changed_fields:
                print(f"    [Dry-Run] Profile Fields Updated: {', '.join(changed_fields)}")
            continue
            
        # Real merge implementation
        # 1. Merge fields
        fields_modified = False
        for _, dup, _ in duplicates_to_merge:
            if merge_patient_fields(master, dup):
                fields_modified = True
                
        # Save updated master profile
        if fields_modified:
            hms.db.save('patients', master, 'patient_id')
            print(f"    Saved updated master profile ID={master.patient_id}")
            
        # 2. Update related tables and delete duplicates
        group_records_moved = 0
        for _, dup, counts in duplicates_to_merge:
            dup_id = dup.patient_id
            
            # Move clinical records
            for table, (model_cls, id_field) in table_models.items():
                conn = hms.db.get_connection()
                cursor = conn.cursor()
                cursor.execute(f"SELECT * FROM {table} WHERE patient_id = ?", (dup_id,))
                rows = cursor.fetchall()
                conn.close()
                
                for row in rows:
                    record_obj = hms.db._row_to_obj(model_cls, row)
                    record_obj.patient_id = master.patient_id
                    hms.db.save(table, record_obj, id_field)
                    group_records_moved += 1
                    total_clinical_records_moved += 1
                    
            # Move files in JSON cache if any
            if dup_id in hms.patient_files:
                if master.patient_id not in hms.patient_files:
                    hms.patient_files[master.patient_id] = []
                hms.patient_files[master.patient_id].extend(hms.patient_files.pop(dup_id))
                
            if dup_id in hms.patient_scheme:
                # Merge schemes
                if master.patient_id not in hms.patient_scheme:
                    hms.patient_scheme[master.patient_id] = hms.patient_scheme.pop(dup_id)
                else:
                    hms.patient_scheme.pop(dup_id)
                    
            # Delete duplicate patient record from both SQLite and Supabase
            hms.db.delete('patients', dup_id, 'patient_id')
            print(f"    Permanently deleted duplicate ID={dup_id}")
            
        print(f"    Success: Merged duplicates into ID={master.patient_id}. Clinical records moved: {group_records_moved}")
        successful_merges += 1
        
    if not dry_run:
        # Save complete JSON state and trigger Supabase JSON sync
        hms.save_data()
        print(f"\n=== MERGE COMPLETED ===")
        print(f"Successfully merged {successful_merges} patient groups.")
        print(f"Consolidated {total_clinical_records_moved} related clinical records.")
        print(f"New patient count: {hms.get_patients_count()}")

if __name__ == '__main__':
    dry_run = '--execute' not in sys.argv
    execute_merge(dry_run=dry_run)
