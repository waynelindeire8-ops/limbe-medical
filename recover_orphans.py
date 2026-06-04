import sqlite3
import json
import os

def recover_orphans():
    conn = sqlite3.connect('hospital_data.db')
    cursor = conn.cursor()
    
    # Get all unique orphaned IDs
    tables = ['appointments', 'medical_records', 'prescriptions', 'bills', 'lab_results', 'queue']
    orphan_ids = set()
    for table in tables:
        cursor.execute(f"SELECT DISTINCT patient_id FROM {table} WHERE patient_id NOT IN (SELECT patient_id FROM patients)")
        orphan_ids.update([row[0] for row in cursor.fetchall() if row[0] and row[0].strip()])
    
    if not orphan_ids:
        print("No orphaned IDs to recover.")
    else:
        print(f"Found {len(orphan_ids)} orphaned IDs.")

    print(f"Attempting to recover names for orphaned IDs...")
    
    recovered_data = {} # id -> {first_name, last_name, ...}
    
    # 1. Check activity log in JSON
    json_path = r"C:\Users\user\OneDrive\Limbe Medical\hospital_data.json"
    if os.path.exists(json_path):
        with open(json_path, 'r', encodicccng='utf-8') as f:
            data = json.load(f)
            for act in data.get('activity', []):
                eid = act.get('entity_id')
                if eid in orphan_ids and act.get('entity') == 'patient' and act.get('summary'):
                    name_parts = act.get('summary').split()
                    if name_parts:
                        recovered_data[eid] = {
                            'first_name': name_parts[0],
                            'last_name': " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                        }
                        print(f"      Found name in JSON logs: {eid} -> {act.get('summary')}")

    # 1.5 Check system_logs in database
    print("      Checking system_logs table...")
    cursor.execute("SELECT entity_id, details FROM system_logs WHERE entity_type = 'Patient' AND details != ''")
    for eid, details in cursor.fetchall():
        if eid in orphan_ids and eid not in recovered_data:
            name_parts = details.split()
            if name_parts:
                recovered_data[eid] = {
                    'first_name': name_parts[0],
                    'last_name': " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                }
                print(f"      Found name in DB logs: {eid} -> {details}")

    # 1.6 Check messages table for names in brackets like "Name (ID)"
    print("      Checking messages table for 'Name (ID)' pattern...")
    import re
    cursor.execute("SELECT content FROM messages WHERE content LIKE '%(%)%'")
    for row in cursor.fetchall():
        content = row[0]
        match = re.search(r"^(.*?)\s*\((.*?)\)", content)
        if match:
            name = match.group(1).strip()
            msg_eid = match.group(2).strip()
            
            # Match msg_eid against orphan_ids (exact or prefix)
            for oid in orphan_ids:
                if (oid == msg_eid or msg_eid.startswith(oid) or oid.startswith(msg_eid)) and oid != '':
                    if oid not in recovered_data:
                        name_parts = name.split()
                        if name_parts:
                            recovered_data[oid] = {
                                'first_name': name_parts[0],
                                'last_name': " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                            }
                            print(f"      Found name in messages: {oid} -> {name}")
                            break
    
    # 2. Check medical_records summary or other fields
    for eid in orphan_ids:
        if eid not in recovered_data:
            for table in tables:
                try:
                    cursor.execute(f"PRAGMA table_info({table})")
                    cols = [row[1] for row in cursor.fetchall()]
                    if 'patient_name' in cols:
                        cursor.execute(f"SELECT patient_name FROM {table} WHERE patient_id = ? AND patient_name != '' LIMIT 1", (eid,))
                        res = cursor.fetchone()
                        if res:
                            name_parts = res[0].split()
                            recovered_data[eid] = {
                                'first_name': name_parts[0],
                                'last_name': " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                            }
                            print(f"      Found name in table {table}: {eid} -> {res[0]}")
                            break
                except:
                    pass

    # 3. Create or update patient records
    from main import HospitalManagementSystem
    from models import Patient
    hms = HospitalManagementSystem()
    
    restored = 0
    updated = 0
    for eid, info in recovered_data.items():
        if eid and info['first_name']:
            existing = hms.get_patient(eid)
            if not existing:
                p = Patient(
                    patient_id=eid,
                    first_name=info['first_name'],
                    last_name=info['last_name'],
                    created_date=datetime.datetime.now().strftime("%Y-%m-%d")
                )
                if hms.add_patient(p):
                    restored += 1
                    print(f"  Restored: {eid} ({info['first_name']} {info['last_name']})")
            elif existing.first_name == "Unknown":
                if hms.update_patient(eid, first_name=info['first_name'], last_name=info['last_name']):
                    updated += 1
                    print(f"  Updated: {eid} -> {info['first_name']} {info['last_name']}")
            else:
                # Already exists and has a name, maybe update last name if missing?
                if not existing.last_name and info['last_name']:
                     if hms.update_patient(eid, last_name=info['last_name']):
                         updated += 1
                         print(f"  Updated last name: {eid} -> {info['last_name']}")

    # 4. Final skeleton pass
    for eid in orphan_ids:
        if eid and not hms.get_patient(eid):
            p = Patient(
                patient_id=eid,
                first_name="Unknown",
                last_name=f"(ID: {eid})",
                created_date=datetime.datetime.now().strftime("%Y-%m-%d")
            )
            if hms.add_patient(p):
                restored += 1
                print(f"  Restored skeleton: {eid}")

    print(f"\nRecovery Summary:")
    print(f"Total new patients recovered: {restored}")
    print(f"Total existing patients updated with better names: {updated}")
    conn.close()

if __name__ == "__main__":
    import datetime
    recover_orphans()
