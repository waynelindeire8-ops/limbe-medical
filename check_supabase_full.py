import os
import sqlite3
from dataclasses import fields
from supabase_data_manager import get_supabase_client
from config.supabase_config import SupabaseConfig
from main import HospitalManagementSystem
from models import Patient

def check_supabase():
    print("Checking Supabase Cloud...")
    try:
        client = get_supabase_client()
        if not client:
            print("Could not initialize Supabase client.")
            return

        # Try to get all patients
        table_name = SupabaseConfig.TABLES.get('patients', 'patients')
        print(f"Fetching from table: {table_name}")
        
        response = client.table(table_name).select("*").execute()
        records = response.data
        
        if records:
            print(f"Found {len(records)} patients in Supabase.")
            
            # Get local IDs
            conn = sqlite3.connect('hospital_data.db')
            cursor = conn.cursor()
            cursor.execute("SELECT patient_id FROM patients")
            local_ids = {row[0] for row in cursor.fetchall()}
            conn.close()
            
            missing_records = [r for r in records if r.get('patient_id') not in local_ids]
            
            if missing_records:
                print(f"Found {len(missing_records)} patients in Supabase that are NOT in the local database.")
                hms = HospitalManagementSystem()
                restored = 0
                for r in missing_records:
                    try:
                        # Map Supabase dict to Patient dataclass
                        # Filter out fields that don't exist in Patient dataclass
                        valid_fields = {f.name for f in fields(Patient)}
                        p_data = {k: v for k, v in r.items() if k in valid_fields}
                        
                        # Ensure all required fields are present
                        if 'patient_id' in p_data and 'first_name' in p_data:
                            p = Patient(**p_data)
                            if hms.add_patient(p):
                                restored += 1
                        else:
                            print(f"    Skipping record with missing required fields: {r.get('patient_id')}")
                    except Exception as e:
                        print(f"    Error restoring {r.get('patient_id')}: {e}")
                print(f"Successfully restored {restored} patients from Supabase.")
            else:
                print("All patients in Supabase are already in the local database.")
        else:
            print("No patients found in Supabase.")
            
        # Also check for any other tables that might contain patients
        print("\nChecking for other potential data tables...")
        # Note: We can't easily list tables in Supabase via the client, but we can try known ones
        potential_tables = ['patient_data', 'legacy_patients', 'archive_patients']
        for pt in potential_tables:
            try:
                res = client.table(pt).select("*", count='exact').execute()
                if res.data:
                    print(f"Found {len(res.data)} records in potential table '{pt}'!")
            except:
                pass

    except Exception as e:
        print(f"Error checking Supabase: {e}")

if __name__ == "__main__":
    check_supabase()
