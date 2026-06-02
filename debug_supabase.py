
import os
import sys

try:
    from supabase import create_client
    print("Supabase library found.")
except ImportError:
    print("Supabase library NOT found.")
    sys.exit(1)

def main():
    url = "https://qiudxdvssvkbpoovwpbr.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFpdWR4ZHZzc3ZrYnBvb3Z3cGJyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTUyOTQ2NywiZXhwIjoyMDgxMTA1NDY3fQ.WoHT4S5Or9sjs4TpB9gpq4ys5F9MlTNiToZA8dOfUPw"
    
    print(f"Testing connection to {url}...")
    try:
        client = create_client(url, key)
        print("Client initialized.")
        
        tables = ['patients', 'doctors']
        for t in tables:
            print(f"Checking table: {t}")
            try:
                res = client.table(t).select("*", count='exact').execute()
                print(f"SUCCESS: {t} has {res.count} records.")
            except Exception as e:
                print(f"FAILURE for {t}: {e}")
    except Exception as e:
        print(f"INIT ERROR: {e}")

if __name__ == "__main__":
    main()
