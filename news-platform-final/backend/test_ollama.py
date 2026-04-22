
import requests
import json

url = "http://localhost:11434/api/generate"
payload = {
    "model": "llama3.2:1b",
    "prompt": "Translate this to Telugu: 'Hello, how are you?'. Just give the translation, nothing else.",
    "stream": False
}

try:
    response = requests.post(url, json=payload)
    print("Response:", response.json().get('response'))
except Exception as e:
    print("Error:", e)
