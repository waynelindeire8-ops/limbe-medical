import os
import json
from supabase import create_client, Client

def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_API_KEY")
    if not url or not key:
        return None
    return create_client(url, key)

def supabase_connected() -> bool:
    return get_supabase_client() is not None

def get_supabase_json() -> dict:
    client = get_supabase_client()
    if not client:
        return None
    try:
        bucket = os.environ.get("SUPABASE_BUCKET", "hospital")
        object_path = os.environ.get("SUPABASE_OBJECT_PATH", "hospital.json")
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
        object_path = os.environ.get("SUPABASE_OBJECT_PATH", "hospital.json")
        json_str = json.dumps(data)
        # Upload to storage
        # We need to overwrite if it exists.
        client.storage.from_(bucket).upload(object_path, json_str.encode(), {"upsert": "true"})
        return True
    except Exception as e:
        print(f"Error saving data to Supabase: {e}")
        return False
