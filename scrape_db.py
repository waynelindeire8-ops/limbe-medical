import os
import re

def scrape_strings(file_path):
    if not os.path.exists(file_path):
        return
    
    print(f"\n--- Scraping {file_path} ---")
    with open(file_path, 'rb') as f:
        content = f.read()
    
    # Find things that look like names or IDs
    # IDs are like P... or numbers
    # Names are Title Case
    strings = re.findall(b"[A-Z][a-z]{2,15}", content)
    unique_strings = sorted(list(set(strings)))
    
    print(f"Found {len(unique_strings)} capitalized words.")
    for s in unique_strings[:50]:
        print(s.decode('utf-8', errors='ignore'))

for f in ['data/hospital_archive_2023.db', 'data/hospital_backup_2024_01.db', 'data/hospital_backup_2024_02.db', 'data/hospital_backup_2024_03.db']:
    scrape_strings(f)
