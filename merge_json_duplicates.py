"""
Merge duplicate patients in the Supabase Storage JSON file (hospital_data.json).
The web app on Render downloads this file and uses it as the data source.

Usage:
  python merge_json_duplicates.py          # dry run - preview only
  python merge_json_duplicates.py --execute # actually merge and upload
"""

import sys
import os
import re
import json
from collections import defaultdict

sys.path.append(os.path.abspath('c:/Users/user/limbe-medical'))

from supabase_data_manager import get_supabase_client

# ── helpers ──────────────────────────────────────────────────────────────────

def normalize(name):
    return re.sub(r'[^a-z]', '', (name or '').lower())

def ids_similar(id1, id2):
    c1 = re.sub(r'[^a-z0-9]', '', (id1 or '').lower())
    c2 = re.sub(r'[^a-z0-9]', '', (id2 or '').lower())
    if c1 == c2:
        return True
    # Count matching prefix characters
    prefix = 0
    for a, b in zip(c1, c2):
        if a == b:
            prefix += 1
        else:
            break
    return prefix >= 8

def score_patient(p, all_medical_records, all_appointments, all_bills, all_prescriptions, all_lab_results):
    s = 0
    pid = p.get('patient_id', '')
    for f in ['date_of_birth','gender','phone','email','address',
              'emergency_contact','blood_group','scheme_provider','scheme_type']:
        v = (p.get(f) or '').strip()
        if v and v.lower() not in ('none','null','n/a',''):
            s += 1
    s += sum(1 for r in all_medical_records if r.get('patient_id') == pid) * 5
    s += sum(1 for r in all_appointments if r.get('patient_id') == pid) * 3
    s += sum(1 for r in all_bills if r.get('patient_id') == pid) * 2
    s += sum(1 for r in all_prescriptions if r.get('patient_id') == pid) * 2
    s += sum(1 for r in all_lab_results if r.get('patient_id') == pid) * 2
    # Prefer IDs without dashes at the end
    if pid and pid[-2:] not in ('-0', '-1', '-2', '-3', '-4', '-5', '-6', '-7', '-8', '-9'):
        s += 0.5
    return s

def merge_fields(master, dup):
    """Copy filled dup fields into master where master is empty. Returns (updated, changed)."""
    updated = dict(master)
    changed = False
    for f in ['date_of_birth','gender','phone','email','address',
              'emergency_contact','blood_group','scheme_provider','scheme_type']:
        mv = (master.get(f) or '').strip()
        dv = (dup.get(f) or '').strip()
        if (not mv or mv.lower() in ('none','null','n/a')) and dv and dv.lower() not in ('none','null','n/a'):
            updated[f] = dv
            changed = True
    # medical_history - combine
    mh = (master.get('medical_history') or '').strip()
    dh = (dup.get('medical_history') or '').strip()
    if dh and dh.lower() not in ('none','null','n/a'):
        if not mh or mh.lower() in ('none','null','n/a'):
            updated['medical_history'] = dh
            changed = True
        elif dh not in mh:
            updated['medical_history'] = f"{mh}; {dh}"
            changed = True
    return updated, changed

# ── main ─────────────────────────────────────────────────────────────────────

def run_merge(dry_run=True):
    client = get_supabase_client()
    if not client:
        print("ERROR: Could not connect to Supabase.")
        return

    # Download the JSON from Supabase Storage
    bucket = 'hospital'
    object_path = 'hospital_data.json'
    print(f"Downloading {object_path} from Supabase Storage bucket '{bucket}'...")
    try:
        raw = client.storage.from_(bucket).download(object_path)
        data = json.loads(raw)
        print("Download successful.")
    except Exception as e:
        print(f"ERROR downloading: {e}")
        return

    patients = data.get('patients', [])
    medical_records = data.get('medical_records', [])
    appointments = data.get('appointments', [])
    bills = data.get('bills', [])
    prescriptions = data.get('prescriptions', [])
    lab_results = data.get('lab_results', [])

    print(f"Loaded: {len(patients)} patients, {len(medical_records)} medical records, "
          f"{len(appointments)} appointments, {len(bills)} bills, "
          f"{len(prescriptions)} prescriptions, {len(lab_results)} lab results")

    # Group patients by normalised (first+last) name
    groups = defaultdict(list)
    for p in patients:
        key = (normalize(p.get('first_name', '')), normalize(p.get('last_name', '')))
        groups[key].append(p)

    # Find groups where at least two members have similar IDs
    candidate_groups = []
    for key, members in groups.items():
        if len(members) < 2:
            continue
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                if ids_similar(members[i]['patient_id'], members[j]['patient_id']):
                    candidate_groups.append((key, members))
                    break
            else:
                continue
            break

    print(f"\nFound {len(candidate_groups)} duplicate groups.")
    if dry_run:
        print("=== DRY RUN — no changes will be made ===\n")

    ids_to_remove = set()
    id_remapping = {}  # old_id → master_id

    for key, members in candidate_groups:
        # Score each member
        scored = []
        for p in members:
            s = score_patient(p, medical_records, appointments, bills, prescriptions, lab_results)
            scored.append((s, p))
        scored.sort(key=lambda x: x[0], reverse=True)

        master_score, master = scored[0]
        dups = [(s, p) for s, p in scored[1:]]

        fn = master.get('first_name', '')
        ln = master.get('last_name', '')
        print(f"Group: {fn} {ln}")
        print(f"  Master: {master['patient_id']} (score={master_score:.1f})")
        for s, dup in dups:
            print(f"  Merge:  {dup['patient_id']} (score={s:.1f})")

        if dry_run:
            print()
            continue

        # Merge fields into master
        for _, dup in dups:
            master, changed = merge_fields(master, dup)

        # Update master in patients list
        for idx, p in enumerate(patients):
            if p['patient_id'] == master['patient_id']:
                patients[idx] = master
                break

        # Remap all clinical records from dup IDs → master ID
        for _, dup in dups:
            dup_id = dup['patient_id']
            master_id = master['patient_id']
            id_remapping[dup_id] = master_id
            ids_to_remove.add(dup_id)
            print(f"  -> Remapping {dup_id} -> {master_id}")

        print()

    if dry_run:
        print(f"=== DRY RUN COMPLETE — {len(candidate_groups)} groups would be merged ===")
        return

    # Apply remapping to all clinical tables
    tables_remapped = {'medical_records': 0, 'appointments': 0, 'bills': 0, 'prescriptions': 0, 'lab_results': 0}

    for r in medical_records:
        if r.get('patient_id') in id_remapping:
            r['patient_id'] = id_remapping[r['patient_id']]
            tables_remapped['medical_records'] += 1

    for r in appointments:
        if r.get('patient_id') in id_remapping:
            r['patient_id'] = id_remapping[r['patient_id']]
            tables_remapped['appointments'] += 1

    for r in bills:
        if r.get('patient_id') in id_remapping:
            r['patient_id'] = id_remapping[r['patient_id']]
            tables_remapped['bills'] += 1

    for r in prescriptions:
        if r.get('patient_id') in id_remapping:
            r['patient_id'] = id_remapping[r['patient_id']]
            tables_remapped['prescriptions'] += 1

    for r in lab_results:
        if r.get('patient_id') in id_remapping:
            r['patient_id'] = id_remapping[r['patient_id']]
            tables_remapped['lab_results'] += 1

    print(f"Records remapped: {tables_remapped}")

    # Remove duplicate patients
    original_count = len(patients)
    patients = [p for p in patients if p['patient_id'] not in ids_to_remove]
    removed = original_count - len(patients)
    print(f"Removed {removed} duplicate patient entries (was {original_count}, now {len(patients)})")

    # Save back to data dict
    data['patients'] = patients
    data['medical_records'] = medical_records
    data['appointments'] = appointments
    data['bills'] = bills
    data['prescriptions'] = prescriptions
    data['lab_results'] = lab_results

    # Upload back to Supabase Storage
    print(f"\nUploading merged data back to Supabase Storage ({object_path})...")
    try:
        json_bytes = json.dumps(data).encode('utf-8')
        client.storage.from_(bucket).upload(object_path, json_bytes, {'upsert': 'true', 'contentType': 'application/json'})
        print("Upload successful!")
    except Exception as e:
        print(f"ERROR uploading: {e}")
        # Save backup locally just in case
        backup = 'hospital_data_merged_backup.json'
        with open(backup, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        print(f"Saved backup locally to {backup}")
        return

    print(f"\n=== SUPABASE MERGE COMPLETE ===")
    print(f"Groups merged: {len(candidate_groups)}")
    print(f"Duplicate patients removed: {removed}")

if __name__ == '__main__':
    dry_run = '--execute' not in sys.argv
    run_merge(dry_run=dry_run)
