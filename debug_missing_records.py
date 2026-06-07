import sqlite3

def find_patients():
    try:
        conn = sqlite3.connect('hospital_data.db')
        conn.row_factory = sqlite3.Row
        
        # Search for the patients the user mentioned
        search_terms = ['Sakina', 'Ndala', 'Atupele', 'chikaonda']
        query = "SELECT patient_id, first_name, last_name FROM patients WHERE "
        clauses = []
        for term in search_terms:
            clauses.append(f"first_name LIKE '%{term}%'")
            clauses.append(f"last_name LIKE '%{term}%'")
        query += " OR ".join(clauses)
        
        patients = conn.execute(query).fetchall()
        print("Found Patients:")
        for p in patients:
            p_dict = dict(p)
            print(f"ID: {p_dict['patient_id']} | Name: {p_dict['first_name']} {p_dict['last_name']}")
            
            # Check for records for this patient
            records = conn.execute("SELECT record_id, date, consult_reason FROM medical_records WHERE patient_id = ? ORDER BY date DESC", (p_dict['patient_id'],)).fetchall()
            print(f"  Records: {len(records)}")
            for r in records:
                r_dict = dict(r)
                print(f"    - {r_dict['date']}: {r_dict['consult_reason']} ({r_dict['record_id']})")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_patients()
