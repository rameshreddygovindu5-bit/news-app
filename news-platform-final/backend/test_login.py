import requests
import json

# Test the login endpoint
url = "http://localhost:8005/api/auth/login"
data = {
    "username": "admin",
    "password": "admin123"
}

try:
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Success! Token: {result.get('access_token', 'N/A')}")
    else:
        print(f"Login failed with status: {response.status_code}")
        
except Exception as e:
    print(f"Error: {e}")
