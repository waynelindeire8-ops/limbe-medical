import sqlite3

conn = sqlite3.connect('hospital_data.db')
cursor = conn.cursor()

ids = [
    '0013099', '0014400', '160057138', '180163876', '180198967', 
    '2100774-04', '2100774-05', '320376304', '80001854408', '800030341*', 
    '800030341-01', '800030341-02', '900000695', '900010024', 
    '90001025804', '90002336402', '903205820', '970031724'
]

for target_id in ids:
    print(f"\nSearching for {target_id} in messages...")
    cursor.execute("SELECT content FROM messages WHERE content LIKE ?", (f"%{target_id}%",))
    rows = cursor.fetchall()
    for r in rows:
        print(f"  {r[0]}")

conn.close()
