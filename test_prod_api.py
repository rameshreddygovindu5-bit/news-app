import requests
import json
try:
    res = requests.get("https://peoples-feedback.com/api/articles", params={"lang": "te", "flags": "A,Y", "page_size": 5}, timeout=10)
    print(f"Status: {res.status_code}")
    if res.status_code == 200:
        data = res.json()
        print(f"Count: {len(data.get('articles', []))}")
        print(f"Total: {data.get('total_count')}")
    else:
        print(f"Response: {res.text[:200]}")
except Exception as e:
    print(f"Error: {e}")
