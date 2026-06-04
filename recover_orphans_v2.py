
import sqlite3

def check_orphans():
    conn = sqlite3.connect('hospital_data.db')
    cursor = conn.cursor()
    
    tables = ['appointments', 'medical_records', 'prescriptions', 'bills', 'lab_results', 'queue']
    all_orphans = set()
    
    print("Checking for orphaned records in clinical tables...")
    for table in tables:
        try:
            cursor.execute(f"SELECT DISTINCT patient_id FROM {table} WHERE patient_id NOT IN (SELECT patient_id FROM patients)")
            orphans = [row[0] for row in cursor.fetchall() if row[0]]
            if orphans:
                print(f" - Found {len(orphans)} orphaned patient IDs in {table}")
                all_orphans.update(orphans)
        except Exception as e:
            print(f" - Error checking {table}: {e}")
            
    print(f"\nTotal unique orphaned patient IDs: {len(all_orphans)}")
    
    if all_orphans:
        print("Restoring skeleton records for orphans...")
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d")
        
        for pid in all_orphans:
            cursor.execute("INSERT INTO patients (patient_id, first_name, last_name, created_date, is_deleted) VALUES (?, ?, ?, ?, 0)",
                         (pid, "Restored", "Orphan", now))
        conn.commit()
        print(f"Successfully restored {len(all_orphans)} skeleton records.")
    
    cursor.execute("SELECT COUNT(*) FROM patients")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM patients WHERE is_deleted = 0")
    active = cursor.fetchone()[0]
    
    print(f"\nFinal Database State:")
    print(f"Total Patients: {total}")
    print(f"Active Patients: {active}")
    
    conn.close()

if __name__ == "__main__":
    check_orphans()
