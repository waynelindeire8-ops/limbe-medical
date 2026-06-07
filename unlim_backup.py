import os
import asyncio
from telethon import TelegramClient
from datetime import datetime
import logging

# Configuration
# Using common Android official keys as a more reliable fallback
API_ID = 35355377
API_HASH = '29ef19a8850934360059ca28bdf1c81e'
PHONE = '+265880861606'
PASSWORD = 'Way@1234$'
DB_FILE = 'hospital_data.db'
SESSION_NAME = 'unlim_backup_session'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def upload_backup():
    if not os.path.exists(DB_FILE):
        logger.error(f"Database file {DB_FILE} not found.")
        return

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            logger.info("Client not authorized. Starting authentication...")
            print("\n" + "="*50)
            print("FIRST-TIME LOGIN REQUIRED")
            print(f"Sending OTP to Telegram for {PHONE}...")
            print("Please enter the code you receive below.")
            print("="*50 + "\n")
            try:
                await client.start(phone=PHONE, password=PASSWORD)
            except Exception as e:
                logger.error(f"Authentication failed: {e}")
                return

        # Upload to "Saved Messages" (self)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        caption = f"Limbe Medical Clinic Backup - {timestamp}"
        
        logger.info(f"Uploading {DB_FILE} to Unlim Cloud (Telegram)...")
        await client.send_file('me', DB_FILE, caption=caption)
        logger.info("Upload successful!")
        
    except Exception as e:
        logger.error(f"Error during backup: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    # When run directly, it will prompt for OTP if not authorized
    loop = asyncio.get_event_loop()
    loop.run_until_complete(upload_backup())
