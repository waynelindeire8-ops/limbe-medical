import os
import json
from supabase import create_client, Client

_supabase_client = None

def get_supabase_client() -> Client:
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

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
        _supabase_client = create_client(url, key)
        return _supabase_client
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

def upload_file_to_supabase(local_path: str, supabase_path: str, bucket: str = "attachments") -> bool:
    client = get_supabase_client()
    if not client:
        return False
    try:
        # Sanitize path: force forward slashes and remove bucket name prefix
        clean_path = supabase_path.replace('\\', '/')
        if clean_path.startswith(f"{bucket}/"):
            clean_path = clean_path.replace(f"{bucket}/", "", 1)
            
        with open(local_path, 'rb') as f:
            response = client.storage.from_(bucket).upload(clean_path, f, {"upsert": "true"})
        return response.status_code == 200
    except Exception as e:
        print(f"Error uploading to Supabase: {e}")
        return False

def delete_file_from_supabase(supabase_path: str, bucket: str = "attachments") -> bool:
    client = get_supabase_client()
    if not client:
        return False
    try:
        # Sanitize path: force forward slashes and remove bucket name prefix
        clean_path = supabase_path.replace('\\', '/')
        if clean_path.startswith(f"{bucket}/"):
            clean_path = clean_path.replace(f"{bucket}/", "", 1)
        
        response = client.storage.from_(bucket).remove([clean_path])
        return True
    except Exception as e:
        print(f"Error deleting from Supabase: {e}")
        return False

def list_files_in_supabase_folder(folder_path: str, bucket: str = "attachments") -> list:
    """Lists all files in a specific Supabase storage folder."""
    client = get_supabase_client()
    if not client:
        return []
    try:
        # Sanitize path: force forward slashes
        clean_path = folder_path.replace('\\', '/')
        if clean_path.startswith(f"{bucket}/"):
            clean_path = clean_path.replace(f"{bucket}/", "", 1)
            
        # Supabase list() returns a list of dictionaries with file metadata
        response = client.storage.from_(bucket).list(clean_path)
        
        # Filter out directories (where 'id' is None or 'metadata' is empty depending on version)
        files = []
        for item in response:
            if item.get('id'): # Only files have IDs
                files.append({
                    'name': item['name'],
                    'size': item.get('metadata', {}).get('size', 0),
                    'mimetype': item.get('metadata', {}).get('mimetype', ''),
                    'created_at': item.get('created_at', '')
                })
        return files
    except Exception as e:
        print(f"Error listing files in Supabase: {e}")
        return []

def get_supabase_file_url(path: str, bucket: str = "attachments") -> str:
    """Gets the public URL for a file in Supabase storage."""
    client = get_supabase_client()
    if not client:
        return ""
    try:
        clean_path = path.replace('\\', '/')
        if clean_path.startswith(f"{bucket}/"):
            clean_path = clean_path.replace(f"{bucket}/", "", 1)
        return client.storage.from_(bucket).get_public_url(clean_path)
    except Exception:
        return ""
        response = client.storage.from_(bucket).remove([clean_path])
        return response.status_code == 200
    except Exception as e:
        print(f"Error deleting from Supabase: {e}")
        return False

def download_file_from_supabase(supabase_path: str, bucket: str = "attachments") -> bytes:
    client = get_supabase_client()
    if not client:
        return None
    try:
        # Sanitize path: force forward slashes and remove bucket name prefix
        clean_path = supabase_path.replace('\\', '/')
        if clean_path.startswith(f"{bucket}/"):
            clean_path = clean_path.replace(f"{bucket}/", "", 1)
            
        return client.storage.from_(bucket).download(clean_path)
    except Exception as e:
        print(f"Error downloading from Supabase: {e}")
        return None

def get_public_url(supabase_path: str, bucket: str = "attachments") -> str:
    client = get_supabase_client()
    if not client:
        return ""
    try:
        # Sanitize path: force forward slashes and remove bucket name prefix
        clean_path = supabase_path.replace('\\', '/')
        if clean_path.startswith(f"{bucket}/"):
            clean_path = clean_path.replace(f"{bucket}/", "", 1)
            
        return client.storage.from_(bucket).get_public_url(clean_path)
    except Exception as e:
        print(f"Error getting public URL: {e}")
        return ""
