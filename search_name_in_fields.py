import sqlite3

def search_name_in_records():
    conn = sqlite3.connect('hospital_data.db')
    cursor = conn.cursor()
    
    search_terms = ['Sakina', 'Ndala', 'Atupele', 'chikaonda']
    print(f"Searching for terms in medical_records fields: {search_terms}")
    
    for term in search_terms:
        query = """
            SELECT record_id, patient_id, date, diagnosis, notes 
            FROM medical_records 
            WHERE diagnosis LIKE ? OR notes LIKE ? OR consult_reason LIKE ?
        """
        val = f"%{term}%"
        cursor.execute(query, (val, val, val))
        results = cursor.fetchall()
        if results:
            print(f"Found '{term}' in records:")
            for r in results:
                print(f"  {r}")
        else:
            print(f"NOT FOUND: {term}")
            
    conn.close()

if __name__ == "__main__":
    search_name_in_records()
