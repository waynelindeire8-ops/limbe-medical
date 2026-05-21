import sqlite3
import os

def check_and_delete():
    db_path = "hospital_data.db"
    if not os.path.exists(db_path):
        print("DB not found")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM doctors")
    total = cursor.fetchone()[0]
    print(f"Total doctors before: {total}")
    
    cursor.execute("SELECT DISTINCT specialty FROM doctors")
    specs = cursor.fetchall()
    print(f"Specialties found: {specs}")
    
    cursor.execute("DELETE FROM doctors WHERE specialty = 'GENERAL'")
    deleted = cursor.rowcount
    print(f"Deleted {deleted} doctors with specialty = 'GENERAL'")
    
    cursor.execute("DELETE FROM doctors WHERE specialty = 'General'")
    deleted2 = cursor.rowcount
    print(f"Deleted {deleted2} doctors with specialty = 'General'")
    
    cursor.execute("SELECT COUNT(*) FROM doctors")
    total_after = cursor.fetchone()[0]
    print(f"Total doctors after: {total_after}")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    check_and_delete()
