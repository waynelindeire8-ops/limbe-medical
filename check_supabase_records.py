from supabase_data_manager import get_supabase_client
from config.supabase_config import SupabaseConfig
import datetime

def check_recent_records():
    client = get_supabase_client()
    if not client:
        print("No client")
        return
        
    table_name = SupabaseConfig.TABLES.get('medical_records', 'medical_records')
    print(f"Checking table: {table_name}")
    
    # Today's date
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    print(f"Searching for records from: {today}")
    
    try:
        # Try both date formats
        response = client.table(table_name).select("*").or_(f"date.eq.{today},date.ilike.{today}%").execute()
        records = response.data
        print(f"Found {len(records)} records from today in Supabase.")
        for r in records:
            print(f"Record ID: {r.get('record_id')} | Patient ID: {r.get('patient_id')} | Date: {r.get('date')}")
            
        if not records:
            # Check all records from today without filter just in case
            response = client.table(table_name).select("*").order("date", descending=True).limit(10).execute()
            print("\nLast 10 records in Supabase:")
            for r in response.data:
                print(f"Record ID: {r.get('record_id')} | Patient ID: {r.get('patient_id')} | Date: {r.get('date')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_recent_records()
