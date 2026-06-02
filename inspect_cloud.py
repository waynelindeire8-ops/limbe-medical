
import os
import json
import sys
from supabase_data_manager import get_supabase_json

def inspect_cloud_data():
    print("Attempting to fetch data from Supabase Storage...")
    try:
        data = get_supabase_json()
        if not data:
            print("FAILURE: No data returned from Supabase Storage.")
            return

        print("SUCCESS: Data retrieved.")
        print(f"Keys found: {list(data.keys())}")
        
        patients = data.get('patients', [])
        print(f"Patient count: {len(patients)}")
        
        if patients:
            print("Sample patient data:")
            print(json.dumps(patients[0], indent=2))
        
        # Check for other clinical data
        for key in ['appointments', 'medical_records', 'bills']:
            count = len(data.get(key, []))
            print(f"Table '{key}': {count} records")

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    inspect_cloud_data()
