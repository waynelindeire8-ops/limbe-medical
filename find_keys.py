import json
path = r"c:\Users\user\OneDrive\Limbe Medical\hospital_data.json"
with open(path, 'r', encoding='utf-8') as f:
    # Read only the beginning of the file to find keys
    content = ""
    for line in f:
        content += line
        if len(content) > 10000: # 10KB should be enough to find main keys
            break
    
    # This is a bit hacky but let's see
    print("Keys found in JSON (approximate):")
    import re
    keys = re.findall(r'"([^"]+)":', content)
    # Filter for top-level keys (those followed by [ or {)
    top_keys = re.findall(r'"([^"]+)":\s*[\[\{]', content)
    print(set(top_keys))
