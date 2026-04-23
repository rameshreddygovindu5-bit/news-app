import requests
import json
try:
    res = requests.get("http://localhost:8005/api/articles", params={"flags": "A,Y", "page_size": 1}, timeout=5)
    print(f"Status: {res.status_code}")
    print(f"Data: {json.dumps(res.json())[:100]}...")
except Exception as e:
    print(f"Error: {e}")
