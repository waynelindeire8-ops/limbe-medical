"""
Supabase Configuration and Integration
"""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class SupabaseConfig:
    """Supabase configuration and connection management"""
    
    # Supabase credentials (using user's provided fallback for Render free plan stability)
    SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://qiudxdvssvkbpoovwpbr.supabase.co').strip()
    SUPABASE_KEY = (os.getenv('SUPABASE_SERVICE_ROLE') or os.getenv('SUPABASE_API_KEY') or 
                   'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFpdWR4ZHZzc3ZrYnBvb3Z3cGJyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTUyOTQ2NywiZXhwIjoyMDgxMTA1NDY3fQ.WoHT4S5Or9sjs4TpB9gpq4ys5F9MlTNiToZA8dOfUPw').strip()
    SUPABASE_SERVICE_KEY = SUPABASE_KEY
    
    # Database tables
    TABLES = {
        'patients': 'patients',
        'doctors': 'doctors',
        'appointments': 'appointments',
        'medical_records': 'medical_records',
        'prescriptions': 'prescriptions',
        'bills': 'bills',
        'inventory': 'inventory_items',
        'users': 'users',
        'queue': 'queue',
        'lab_results': 'lab_results'
    }
    
    # Connection settings
    TIMEOUT = 10
    RETRY_COUNT = 3
    RETRY_DELAY = 1


class SupabaseClient:
    """Supabase client for database operations"""
    
    def __init__(self):
        self.url = SupabaseConfig.SUPABASE_URL
        self.key = SupabaseConfig.SUPABASE_KEY
        self.service_key = SupabaseConfig.SUPABASE_SERVICE_KEY
        self._client = None
    
    def connect(self):
        """Initialize Supabase client"""
        try:
            from supabase import create_client, Client
            
            # Use the same fallback logic as supabase_data_manager.py
            fallback_url = "https://qiudxdvssvkbpoovwpbr.supabase.co"
            fallback_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFpdWR4ZHZzc3ZrYnBvb3Z3cGJyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTUyOTQ2NywiZXhwIjoyMDgxMTA1NDY3fQ.WoHT4S5Or9sjs4TpB9gpq4ys5F9MlTNiToZA8dOfUPw"
            
            url = self.url if self.url and 'your-project' not in self.url else fallback_url
            key = self.key if self.key and self.key.startswith('eyJ') else fallback_key
            
            self._client = create_client(url, key)
            return True
        except ImportError:
            print("Warning: supabase-py not installed. Install with: pip install supabase")
            return False
        except Exception as e:
            print(f"Error connecting to Supabase: {str(e)}")
            return False
    
    def is_connected(self) -> bool:
        """Check if connected to Supabase"""
        return self._client is not None
    
    def get_client(self):
        """Get Supabase client"""
        if not self.is_connected():
            self.connect()
        return self._client
    
    # CRUD Operations
    def upsert(self, table: str, data: Dict[str, Any]) -> Optional[Dict]:
        """Upsert record into table"""
        try:
            client = self.get_client()
            if not client:
                return None
            
            response = client.table(table).upsert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error upserting into {table}: {str(e)}")
            return None
    
    def insert(self, table: str, data: Dict[str, Any]) -> Optional[Dict]:
        """Insert record into table"""
        return self.upsert(table, data)
    
    def select(self, table: str, filters: Optional[Dict] = None) -> Optional[list]:
        """Select records from table"""
        try:
            client = self.get_client()
            if not client:
                return None
            
            query = client.table(table).select('*')
            
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            response = query.execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error selecting from {table}: {str(e)}")
            return None
    
    def update(self, table: str, id_field: str, id_value: Any, data: Dict[str, Any]) -> Optional[Dict]:
        """Update record in table"""
        try:
            client = self.get_client()
            if not client:
                return None
            
            response = client.table(table).update(data).eq(id_field, id_value).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error updating {table}: {str(e)}")
            return None
    
    def delete(self, table: str, id_field: str, id_value: Any) -> bool:
        """Delete record from table"""
        try:
            client = self.get_client()
            if not client:
                return False
            
            response = client.table(table).delete().eq(id_field, id_value).execute()
            return True
        except Exception as e:
            print(f"Error deleting from {table}: {str(e)}")
            return False
    
    def search(self, table: str, search_field: str, search_value: str) -> Optional[list]:
        """Search records in table"""
        try:
            client = self.get_client()
            if not client:
                return None
            
            response = client.table(table).select('*').ilike(search_field, f'%{search_value}%').execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error searching {table}: {str(e)}")
            return None


# Global Supabase client instance
supabase_client = SupabaseClient()
