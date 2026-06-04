
import sqlite3
import re

def check_merges_carefully():
    conn = sqlite3.connect('hospital_data.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT patient_id FROM patients")
    current_ids = {str(row[0]).strip() for row in cursor.fetchall()}
    
    cursor.execute("SELECT first_name, last_name, patient_id FROM patients")
    current_patients = {f"{f} {l}".lower().replace(" ", ""): pid for f, l, pid in cursor.fetchall()}
    
    potential_missing = {} # ID -> Name
    cursor.execute("SELECT content FROM messages WHERE subject = 'Patient added' OR content LIKE '%(%)%'")
    for row in cursor.fetchall():
        content = row[0]
        match = re.search(r"^(.*?)\s*\((.*?)\)", content)
        if match:
            name = match.group(1).strip()
            pid = match.group(2).strip()
            if pid and pid not in current_ids and name != "Unknown":
                potential_missing[pid] = name

    cursor.execute("SELECT entity_id, details FROM system_logs WHERE entity_type = 'Patient' AND action = 'Add'")
    for pid, details in cursor.fetchall():
        if pid and pid not in current_ids and details and details != "Unknown":
            potential_missing[pid] = details

    print(f"Found {len(potential_missing)} IDs in logs that are currently missing from DB.")
    
    for pid, name in potential_missing.items():
        clean_name = name.lower().replace(" ", "")
        if clean_name in current_patients:
            master_id = current_patients[clean_name]
            print(f" - Merged/Duplicate: {name} (Log ID: {pid} vs DB ID: {master_id})")

    conn.close()

if __name__ == "__main__":
    check_merges_carefully()
