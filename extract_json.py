"""Extract and pretty-print JSON from Punto Farma API response."""

import re
import json

with open("punto_farma_page_1_response.txt", "r") as f:
    response_text = f.read()

# Find the JSON object that starts with "1:{"
match = re.search(r'1:(\{"ok".*\})', response_text)
if match:
    json_str = match.group(1)
    data = json.loads(json_str)

    print("=" * 80)
    print("PUNTO FARMA API RESPONSE - FULL JSON STRUCTURE")
    print("=" * 80)
    print(json.dumps(data, indent=2, ensure_ascii=False))
else:
    print("No JSON found")
