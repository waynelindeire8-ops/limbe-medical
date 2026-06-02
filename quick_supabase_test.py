
import os
from supabase import create_client

def simple_supabase_check():
    # Use hardcoded fallback from supabase_data_manager if env is missing
    url = os.environ.get("SUPABASE_URL", "https://qiudxdvssvkbpoovwpbr.supabase.co").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFpdWR4ZHZzc3ZrYnBvb3Z3cGJyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTUyOTQ2NywiZXhwIjoyMDgxMTA1NDY3fQ.WoHT4S5Or9sjs4TpB9gpq4ys5F9MlTNiToZA8dOfUPw").strip()
    
    print(f"Connecting to: {url}")
    try:
        client = create_client(url, key)
        
        tables = ['patients', 'doctors', 'appointments']
        for t in tables:
            try:
                res = client.table(t).select("*", count='exact').execute()
                print(f"Table '{t}': {len(res.data)} records")
            except Exception as e:
                print(f"Table '{t}': Error {e}")
                
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    simple_supabase_check()
