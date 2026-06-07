import sqlite3

def check_deleted_records():
    conn = sqlite3.connect('hospital_data.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM medical_records WHERE is_deleted = 1")
    deleted_count = cursor.fetchone()[0]
    print(f"Soft-deleted medical records: {deleted_count}")
    
    if deleted_count > 0:
        cursor.execute("SELECT record_id, patient_id, date, diagnosis FROM medical_records WHERE is_deleted = 1 LIMIT 10")
        for row in cursor.fetchall():
            print(row)
            
    conn.close()

if __name__ == "__main__":
    check_deleted_records()
