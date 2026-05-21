import json
import os

def cleanup_json():
    json_path = r"c:\Users\user\OneDrive\Limbe Medical\hospital_data.json"
    if not os.path.exists(json_path):
        print("JSON not found")
        return
        
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'doctors' in data:
            original_count = len(data['doctors'])
            # Remove doctors that look like placeholders (Dr0 Doctor0, etc.)
            data['doctors'] = [d for d in data['doctors'] if not (d.get('first_name', '').startswith('Dr') and d.get('last_name', '').startswith('Doctor'))]
            new_count = len(data['doctors'])
            print(f"Removed {original_count - new_count} doctors from JSON.")
            
            # Also clear departments list if it exists and has General
            if 'departments' in data:
                data['departments'] = [d for d in data['departments'] if d.lower() != 'general']
                print("Cleaned up departments list in JSON.")

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            print("JSON updated successfully.")
        else:
            print("No doctors list in JSON.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    cleanup_json()
