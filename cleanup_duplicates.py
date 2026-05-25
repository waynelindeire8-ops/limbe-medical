from main import HospitalManagementSystem

def cleanup():
    hms = HospitalManagementSystem()
    
    # Define duplicate groups to merge
    # Format: (master_id, [duplicate_ids])
    merges = [
        ("17010743501", ["17010742501", "17010743500"]), # Felix Phiri
        ("Pat727d1d85", ["6790", "0032669"]),           # Harrison Malajira
        ("Pb7ac6245", ["P1165d165", "Pd0667e4c"]),      # gilbert chimphepo
        ("289090", ["3464294"]),                         # christina awadi
        ("1984376", ["3421781"]),                        # Gift Maganga
        ("3496965101", ["349696501"]),                   # Glory Jason
        ("160084314", ["16008431401"]),                  # Grace kamangira
        ("0013829", ["P4285785d"]),                      # Agness Sambo (checking name dupes from logs)
    ]
    
    print("--- Starting duplicate cleanup ---")
    
    for master_id, dups in merges:
        print(f"\nMerging group for master ID: {master_id}")
        if hms.merge_patients(master_id, dups):
            print(f"SUCCESS: Merged {len(dups)} duplicates into {master_id}")
        else:
            print(f"FAILED: Could not merge duplicates for {master_id}")
            
    print("\n--- Cleanup Complete ---")
    print(f"Final patient count: {hms.get_patients_count()}")

if __name__ == "__main__":
    cleanup()
