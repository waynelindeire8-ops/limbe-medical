"""
Supabase Configuration and Integration
"""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class SupabaseConfig:
    """Supabase configuration and connection management"""
    
    # Supabase credentials
    SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://your-project.supabase.co')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'your-anon-key')
    SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY', 'your-service-key')
    
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
            self._client = create_client(self.url, self.key)
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
    def insert(self, table: str, data: Dict[str, Any]) -> Optional[Dict]:
        """Insert record into table"""
        try:
            client = self.get_client()
            if not client:
                return None
            
            response = client.table(table).insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error inserting into {table}: {str(e)}")
            return None
    
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
