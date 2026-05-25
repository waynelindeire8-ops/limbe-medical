import sqlite3
from collections import defaultdict

def find_duplicates():
    db_path = 'hospital_data.db'
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        print(f"--- Analyzing duplicates in {db_path} ---")

        # 1. Exact Name Duplicates (First Name + Last Name)
        cursor.execute("""
            SELECT first_name, last_name, COUNT(*) as count 
            FROM patients 
            WHERE is_deleted = 0
            GROUP BY LOWER(first_name), LOWER(last_name) 
            HAVING count > 1
        """)
        name_dupes = cursor.fetchall()
        
        print(f"\n[Name Duplicates] Found {len(name_dupes)} groups:")
        for row in name_dupes:
            name = f"{row['first_name']} {row['last_name']}"
            count = row['count']
            cursor.execute("SELECT patient_id, phone, created_date FROM patients WHERE LOWER(first_name) = LOWER(?) AND LOWER(last_name) = LOWER(?) AND is_deleted = 0", (row['first_name'], row['last_name']))
            details = cursor.fetchall()
            ids = [d['patient_id'] for d in details]
            print(f" - '{name}': {count} entries (IDs: {', '.join(ids)})")

        # 2. Phone Duplicates
        cursor.execute("""
            SELECT phone, COUNT(*) as count 
            FROM patients 
            WHERE phone IS NOT NULL AND phone != '' AND is_deleted = 0
            GROUP BY phone 
            HAVING count > 1
        """)
        phone_dupes = cursor.fetchall()
        
        print(f"\n[Phone Duplicates] Found {len(phone_dupes)} groups:")
        for row in phone_dupes:
            phone = row['phone']
            count = row['count']
            cursor.execute("SELECT patient_id, first_name, last_name FROM patients WHERE phone = ? AND is_deleted = 0", (phone,))
            details = cursor.fetchall()
            names = [f"{d['first_name']} {d['last_name']} ({d['patient_id']})" for d in details]
            print(f" - Phone '{phone}': {count} entries ({', '.join(names)})")

        # 3. Email Duplicates
        cursor.execute("""
            SELECT email, COUNT(*) as count 
            FROM patients 
            WHERE email IS NOT NULL AND email != '' AND is_deleted = 0
            GROUP BY email 
            HAVING count > 1
        """)
        email_dupes = cursor.fetchall()
        
        print(f"\n[Email Duplicates] Found {len(email_dupes)} groups:")
        for row in email_dupes:
            email = row['email']
            count = row['count']
            cursor.execute("SELECT patient_id, first_name, last_name FROM patients WHERE email = ? AND is_deleted = 0", (email,))
            details = cursor.fetchall()
            names = [f"{d['first_name']} {d['last_name']} ({d['patient_id']})" for d in details]
            print(f" - Email '{email}': {count} entries ({', '.join(names)})")

        conn.close()
        print("\n--- Analysis Complete ---")

    except Exception as e:
        print(f"Error during analysis: {e}")

if __name__ == "__main__":
    find_duplicates()
