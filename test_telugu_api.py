import requests
import json
try:
    res = requests.get("http://localhost:8005/api/articles", params={"lang": "te", "flags": "A,Y", "page_size": 5}, timeout=5)
    print(f"Status: {res.status_code}")
    articles = res.json().get("articles", [])
    print(f"Count: {len(articles)}")
    for a in articles:
        print(f" - {a.get('original_title') or a.get('telugu_title')}")
except Exception as e:
    print(f"Error: {e}")
