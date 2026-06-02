import sqlite3

conn = sqlite3.connect('hospital_data.db')
cursor = conn.cursor()

print("Checking for orphaned records...")

tables_with_patient_id = [
    'appointments', 'medical_records', 'prescriptions', 
    'bills', 'lab_results', 'queue'
]

orphans = {}

for table in tables_with_patient_id:
    print(f"  Checking {table}...")
    cursor.execute(f"""
        SELECT DISTINCT patient_id FROM {table} 
        WHERE patient_id NOT IN (SELECT patient_id FROM patients)
    """)
    results = [row[0] for row in cursor.fetchall()]
    if results:
        orphans[table] = results
        print(f"    Found {len(results)} orphaned patient IDs in {table}")

if orphans:
    print("\nOrphaned Patient IDs found:")
    all_orphan_ids = set()
    for table, ids in orphans.items():
        all_orphan_ids.update(ids)
    
    print(f"Total unique orphaned IDs: {len(all_orphan_ids)}")
    for oid in sorted(list(all_orphan_ids))[:20]:
        print(f" - {oid}")
else:
    print("\nNo orphaned records found.")

conn.close()
