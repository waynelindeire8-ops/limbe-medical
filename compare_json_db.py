import sqlite3
import json
from supabase_data_manager import get_supabase_json

def compare_json_and_db():
    print("Fetching Supabase Storage JSON...")
    data = get_supabase_json()
    if not data:
        print("No cloud data.")
        return
        
    cloud_records = data.get('medical_records', [])
    print(f"Total records in Cloud JSON: {len(cloud_records)}")
    
    conn = sqlite3.connect('hospital_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT record_id FROM medical_records")
    db_record_ids = {row[0] for row in cursor.fetchall()}
    conn.close()
    
    print(f"Total records in Local DB: {len(db_record_ids)}")
    
    missing_from_db = [r for r in cloud_records if r.get('record_id') not in db_record_ids]
    
    if missing_from_db:
        print(f"Found {len(missing_from_db)} records in Cloud JSON that are MISSING from local DB!")
        for r in missing_from_db[:10]:
            print(f"  Missing: {r.get('record_id')} : {r.get('date')} : {r.get('diagnosis')}")
    else:
        print("All records in Cloud JSON are present in local DB.")

if __name__ == "__main__":
    compare_json_and_db()
