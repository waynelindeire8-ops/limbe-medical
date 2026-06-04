
import sqlite3
import re
from datetime import datetime

def restore_missing():
    conn = sqlite3.connect('hospital_data.db')
    cursor = conn.cursor()
    
    # 1. Get current patient IDs and Names
    cursor.execute("SELECT patient_id FROM patients")
    current_ids = {str(row[0]).strip() for row in cursor.fetchall()}
    
    cursor.execute("SELECT first_name, last_name FROM patients")
    current_names = {f"{f} {l}".lower().replace(" ", "") for f, l in cursor.fetchall()}
    
    potential_missing = {} # ID -> Name

    # 2. Scan messages for "Patient added"
    cursor.execute("SELECT content FROM messages WHERE subject = 'Patient added' OR content LIKE '%(%)%'")
    for row in cursor.fetchall():
        content = row[0]
        match = re.search(r"^(.*?)\s*\((.*?)\)", content)
        if match:
            name = match.group(1).strip()
            pid = match.group(2).strip()
            if pid and pid not in current_ids and name != "Unknown":
                potential_missing[pid] = name

    # 3. Scan system_logs for "Add" "Patient"
    cursor.execute("SELECT entity_id, details FROM system_logs WHERE entity_type = 'Patient' AND action = 'Add'")
    for pid, details in cursor.fetchall():
        if pid and pid not in current_ids and details and details != "Unknown":
            potential_missing[pid] = details

    # 4. Restore unique names
    restored_count = 0
    now = datetime.now().strftime("%Y-%m-%d")
    
    # We want to restore at least one instance of every name that is missing
    names_to_restore = {} # clean_name -> (id, original_name)
    
    for pid, name in potential_missing.items():
        clean_name = name.lower().replace(" ", "")
        if clean_name not in current_names:
            if clean_name not in names_to_restore:
                names_to_restore[clean_name] = (pid, name)

    print(f"Restoring {len(names_to_restore)} unique patients that were lost...")
    
    for clean_name, (pid, name) in names_to_restore.items():
        name_parts = name.split()
        first = name_parts[0]
        last = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        try:
            cursor.execute("INSERT INTO patients (patient_id, first_name, last_name, created_date, is_deleted) VALUES (?, ?, ?, ?, 0)",
                         (pid, first, last, now))
            restored_count += 1
            print(f" - Restored: {pid} ({name})")
        except Exception as e:
            print(f" - Error restoring {pid}: {e}")

    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM patients")
    total = cursor.fetchone()[0]
    print(f"\nRestoration Complete. Total Patients: {total}")
    conn.close()

if __name__ == "__main__":
    restore_missing()
