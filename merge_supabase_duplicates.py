"""
Merge duplicate patients DIRECTLY in Supabase Postgres tables.
This is needed because the web app on Render reads from Supabase, not local SQLite.
"""

import sys
import os
import re
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
    # shared prefix >= 8 chars
    prefix = 0
    for a, b in zip(c1, c2):
        if a == b:
            prefix += 1
        else:
            break
    return prefix >= 8

def score(p, counts):
    s = 0
    for f in ['date_of_birth','gender','phone','email','address',
              'emergency_contact','blood_group','scheme_provider','scheme_type']:
        v = (p.get(f) or '').strip()
        if v and v.lower() not in ('none','null','n/a'):
            s += 1
    s += sum(counts.values()) * 5
    pid = p.get('patient_id', '')
    if '-' not in pid and ' ' not in pid:
        s += 0.5
    return s

# ── main ─────────────────────────────────────────────────────────────────────

CLINICAL_TABLES = [
    ('appointments',  'patient_id'),
    ('medical_records','patient_id'),
    ('prescriptions', 'patient_id'),
    ('lab_results',   'patient_id'),
    ('queue',         'patient_id'),
]

def fetch_all_patients(client):
    """Pull all non-deleted patients from Supabase in chunks."""
    all_patients = []
    offset = 0
    chunk = 1000
    while True:
        resp = client.table('patients').select('*').eq('is_deleted', 0).range(offset, offset + chunk - 1).execute()
        batch = resp.data or []
        all_patients.extend(batch)
        if len(batch) < chunk:
            break
        offset += chunk
    return all_patients

def get_clinical_counts(client, pid):
    counts = {}
    for table, col in CLINICAL_TABLES:
        try:
            resp = client.table(table).select('*', count='exact').eq(col, pid).execute()
            counts[table] = resp.count or 0
        except Exception:
            counts[table] = 0
    return counts

def merge_fields(master, dup):
    """Copy non-empty dup fields into master where master is empty. Returns updated dict."""
    updated = dict(master)
    changed = False
    for f in ['date_of_birth','gender','phone','email','address',
              'emergency_contact','blood_group','scheme_provider','scheme_type']:
        mv = (master.get(f) or '').strip()
        dv = (dup.get(f) or '').strip()
        if (not mv or mv.lower() in ('none','null','n/a')) and dv and dv.lower() not in ('none','null','n/a'):
            updated[f] = dv
            changed = True
    # medical_history
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

def execute_merge(dry_run=True):
    client = get_supabase_client()
    if not client:
        print("ERROR: Could not connect to Supabase.")
        return

    print("Fetching patients from Supabase...")
    patients = fetch_all_patients(client)
    print(f"Loaded {len(patients)} active patients from Supabase.")

    # Group by normalised name
    groups = defaultdict(list)
    for p in patients:
        key = (normalize(p.get('first_name','')), normalize(p.get('last_name','')))
        groups[key].append(p)

    # Find groups with similar IDs
    candidate_groups = []
    for key, members in groups.items():
        if len(members) < 2:
            continue
        found = False
        for i in range(len(members)):
            for j in range(i+1, len(members)):
                if ids_similar(members[i]['patient_id'], members[j]['patient_id']):
                    found = True
                    break
            if found:
                break
        if found:
            candidate_groups.append((key, members))

    print(f"\nFound {len(candidate_groups)} duplicate groups in Supabase.")
    if dry_run:
        print("=== DRY RUN — no changes will be made ===")

    merged_groups = 0
    records_moved = 0

    for key, members in candidate_groups:
        # Score each member
        scored = []
        for p in members:
            pid = p['patient_id']
            counts = get_clinical_counts(client, pid)
            scored.append((score(p, counts), p, counts))
        scored.sort(key=lambda x: x[0], reverse=True)

        master_score, master, master_counts = scored[0]
        duplicates = scored[1:]

        fn = master.get('first_name','')
        ln = master.get('last_name','')
        print(f"\nGroup: {fn} {ln}")
        print(f" -> Master: {master['patient_id']} (score={master_score})")
        for sc, dup, cnt in duplicates:
            print(f" -> Merge:  {dup['patient_id']} (score={sc}) counts={cnt}")

        if dry_run:
            continue

        # 1. Merge fields into master
        updated_master, changed = dict(master), False
        for _, dup, _ in duplicates:
            updated_master, c = merge_fields(updated_master, dup)
            if c:
                changed = True

        if changed:
            try:
                client.table('patients').update(updated_master).eq('patient_id', master['patient_id']).execute()
                print(f"    Updated master profile {master['patient_id']}")
            except Exception as e:
                print(f"    ERROR updating master: {e}")

        # 2. Move clinical records from duplicates → master
        for _, dup, counts in duplicates:
            dup_id = dup['patient_id']
            master_id = master['patient_id']

            for table, col in CLINICAL_TABLES:
                if counts.get(table, 0) == 0:
                    continue
                try:
                    # Fetch records belonging to the duplicate
                    resp = client.table(table).select('*').eq(col, dup_id).execute()
                    recs = resp.data or []
                    for rec in recs:
                        rec[col] = master_id
                        client.table(table).upsert(rec).execute()
                        records_moved += 1
                    print(f"    Moved {len(recs)} {table} records from {dup_id} → {master_id}")
                except Exception as e:
                    print(f"    ERROR moving {table}: {e}")

            # 3. Delete the duplicate patient
            try:
                client.table('patients').delete().eq('patient_id', dup_id).execute()
                print(f"    Deleted duplicate patient {dup_id}")
            except Exception as e:
                print(f"    ERROR deleting {dup_id}: {e}")

        merged_groups += 1

    if not dry_run:
        print(f"\n=== SUPABASE MERGE COMPLETE ===")
        print(f"Groups merged: {merged_groups}")
        print(f"Clinical records moved: {records_moved}")
    else:
        print(f"\n=== DRY RUN COMPLETE — {len(candidate_groups)} groups would be merged ===")

if __name__ == '__main__':
    dry_run = '--execute' not in sys.argv
    execute_merge(dry_run=dry_run)
