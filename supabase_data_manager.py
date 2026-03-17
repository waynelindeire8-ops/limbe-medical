import os
import json
from supabase import create_client, Client

def get_supabase_client() -> Client:
    # On Render or other cloud platforms, env vars are often strings.
    # We strip whitespace just in case.
    url = os.environ.get("SUPABASE_URL", "").strip()
    # Try service role first, then anon key
    key = os.environ.get("SUPABASE_SERVICE_ROLE", "").strip() or os.environ.get("SUPABASE_API_KEY", "").strip()

    # Hardcoded fallback values (User provided these, essential for Render deployment if env vars fail)
    # The key below is a valid Service Role JWT which is required for storage operations.
    fallback_url = "https://qiudxdvssvkbpoovwpbr.supabase.co"
    fallback_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFpdWR4ZHZzc3ZrYnBvb3Z3cGJyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTUyOTQ2NywiZXhwIjoyMDgxMTA1NDY3fQ.WoHT4S5Or9sjs4TpB9gpq4ys5F9MlTNiToZA8dOfUPw"

    if not url:
        url = fallback_url
    
    # If key is missing OR if it doesn't look like a valid JWT (starts with eyJ), use fallback
    if not key or not key.startswith("eyJ"):
        print("[WARN] Invalid or missing Supabase key detected in env. Using hardcoded service role fallback.")
        key = fallback_key

    if not url or not key:
        print("[ERROR] Supabase credentials missing.")
        return None
        
    try:
        return create_client(url, key)
    except Exception as e:
        print(f"[ERROR] Failed to create Supabase client: {e}")
        return None

def supabase_connected() -> bool:
    return get_supabase_client() is not None

def get_supabase_json() -> dict:
    client = get_supabase_client()
    if not client:
        return None
    try:
        bucket = os.environ.get("SUPABASE_BUCKET", "hospital")
        # Default to hospital_data.json to match the file in the bucket
        object_path = os.environ.get("SUPABASE_OBJECT_PATH", "hospital_data.json")
        print(f"[INFO] Downloading {object_path} from bucket {bucket}...")
        response = client.storage.from_(bucket).download(object_path)
        return json.loads(response)
    except Exception as e:
        print(f"Error getting data from Supabase: {e}")
        return None

def put_supabase_json(data: dict) -> bool:
    client = get_supabase_client()
    if not client:
        return False
    try:
        bucket = os.environ.get("SUPABASE_BUCKET", "hospital")
        object_path = os.environ.get("SUPABASE_OBJECT_PATH", "hospital_data.json")
        json_str = json.dumps(data)
        response = client.storage.from_(bucket).upload(object_path, json_str.encode(), {"upsert": "true"})
        return response.status_code == 200
    except Exception as e:
        print(f"Error saving data to Supabase: {e}")
        return False

def upload_file_to_supabase(local_path: str, supabase_path: str) -> bool:
    client = get_supabase_client()
    if not client:
        return False
    try:
        bucket = os.environ.get("SUPABASE_BUCKET", "hospital")
        with open(local_path, 'rb') as f:
            response = client.storage.from_(bucket).upload(supabase_path, f, {"upsert": "true"})
        return response.status_code == 200
    except Exception as e:
        print(f"Error uploading to Supabase: {e}")
        return False

def delete_file_from_supabase(supabase_path: str) -> bool:
    client = get_supabase_client()
    if not client:
        return False
    try:
        bucket = os.environ.get("SUPABASE_BUCKET", "hospital")
        response = client.storage.from_(bucket).remove([supabase_path])
        return response.status_code == 200
    except Exception as e:
        print(f"Error deleting from Supabase: {e}")
        return False

def get_public_url(supabase_path: str) -> str:
    client = get_supabase_client()
    if not client:
        return ""
    try:
        bucket = os.environ.get("SUPABASE_BUCKET", "hospital")
        return client.storage.from_(bucket).get_public_url(supabase_path)
    except Exception as e:
        print(f"Error getting public URL: {e}")
        return ""
