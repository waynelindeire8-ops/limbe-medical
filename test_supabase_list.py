from supabase_data_manager import list_files_in_supabase_folder

patient_id = "000316201"
print(f"Testing Supabase list for patient {patient_id}...")
files = list_files_in_supabase_folder(patient_id)
print(f"Found {len(files)} files:")
for f in files:
    print(f" - {f['name']} ({f['size']} bytes)")
