
import sqlite3
import re

def find_missing_from_logs():
    conn = sqlite3.connect('hospital_data.db')
    cursor = conn.cursor()
    
    # 1. Get current patient IDs
    cursor.execute("SELECT patient_id FROM patients")
    current_ids = {str(row[0]).strip() for row in cursor.fetchall()}
    
    potential_missing = {} # ID -> Name

    # 2. Scan messages for "Patient added" pattern: "Name (ID)"
    cursor.execute("SELECT content FROM messages WHERE subject = 'Patient added' OR content LIKE '%(%)%'")
    for row in cursor.fetchall():
        content = row[0]
        match = re.search(r"^(.*?)\s*\((.*?)\)", content)
        if match:
            name = match.group(1).strip()
            pid = match.group(2).strip()
            if pid and pid not in current_ids and name != "Unknown":
                potential_missing[pid] = name

    # 3. Scan system_logs for "Add" "Patient" actions
    cursor.execute("SELECT entity_id, details FROM system_logs WHERE entity_type = 'Patient' AND action = 'Add'")
    for pid, details in cursor.fetchall():
        if pid and pid not in current_ids and details and details != "Unknown":
            potential_missing[pid] = details

    print(f"Found {len(potential_missing)} IDs in logs that are NOT in the current patient list.")
    
    # 4. Filter out those that were merged (check if their name exists under a different ID)
    cursor.execute("SELECT first_name, last_name FROM patients")
    current_names = {f"{f} {l}".lower().replace(" ", "") for f, l in cursor.fetchall()}
    
    truly_missing = {}
    for pid, name in potential_missing.items():
        clean_name = name.lower().replace(" ", "")
        if clean_name not in current_names:
            truly_missing[pid] = name

    print(f"Of those, {len(truly_missing)} have names that do not exist at all in the current DB.")
    for pid, name in list(truly_missing.items())[:10]:
        print(f" - Missing: {pid} ({name})")

    conn.close()

if __name__ == "__main__":
    find_missing_from_logs()
