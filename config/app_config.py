# Application Configuration
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')
    DATABASE_FILE = os.getenv('DATABASE_FILE', 'data/hospital.db')
    DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
    APP_NAME = os.getenv('APP_NAME', 'Hospital Management System')
    APP_VERSION = os.getenv('APP_VERSION', '2.0')
