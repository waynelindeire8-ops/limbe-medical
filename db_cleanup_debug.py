import sqlite3
import os

def check_and_delete():
    db_path = "hospital_data.db"
    log_path = "debug_log.txt"
    
    with open(log_path, 'w') as log:
        if not os.path.exists(db_path):
            log.write("DB not found\n")
            return
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM doctors")
        total = cursor.fetchone()[0]
        log.write(f"Total doctors before: {total}\n")
        
        cursor.execute("SELECT DISTINCT specialty FROM doctors")
        specs = cursor.fetchall()
        log.write(f"Specialties found: {specs}\n")
        
        # Check some doctor names
        cursor.execute("SELECT doctor_id, first_name, last_name, specialty FROM doctors LIMIT 5")
        docs = cursor.fetchall()
        log.write(f"Sample doctors: {docs}\n")
        
        cursor.execute("DELETE FROM doctors WHERE specialty = 'GENERAL'")
        deleted = cursor.rowcount
        log.write(f"Deleted {deleted} doctors with specialty = 'GENERAL'\n")
        
        cursor.execute("DELETE FROM doctors WHERE specialty = 'General'")
        deleted2 = cursor.rowcount
        log.write(f"Deleted {deleted2} doctors with specialty = 'General'\n")
        
        # Try deleting by name pattern if that matches what user said
        cursor.execute("DELETE FROM doctors WHERE first_name LIKE 'Dr%' OR first_name LIKE 'Doctor%'")
        deleted3 = cursor.rowcount
        log.write(f"Deleted {deleted3} doctors with name pattern 'Dr%' or 'Doctor%'\n")

        cursor.execute("SELECT COUNT(*) FROM doctors")
        total_after = cursor.fetchone()[0]
        log.write(f"Total doctors after: {total_after}\n")
        
        conn.commit()
        conn.close()
        log.write("Done\n")

if __name__ == "__main__":
    check_and_delete()
