import os
path = r"c:\Users\user\OneDrive\Limbe Medical\hospital_data.json"
if os.path.exists(path):
    print(f"File size: {os.path.getsize(path) / (1024*1024):.2f} MB")
else:
    print("File not found")
