
import os
import sys
from supabase_data_manager import get_supabase_client, get_supabase_json

print("Testing Supabase connection...")

client = get_supabase_client()
if not client:
    print("FAIL: Could not create Supabase client.")
    sys.exit(1)
else:
    print("SUCCESS: Supabase client created.")

print("Testing data download...")
data = get_supabase_json()
if data:
    print("SUCCESS: Data downloaded successfully.")
    print(f"Keys in data: {list(data.keys())}")
else:
    print("FAIL: Data download failed (or file is empty/missing).")
