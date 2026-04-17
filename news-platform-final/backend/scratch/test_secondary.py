from google import genai

api_key = "AIzaSyDOqGA7f69IcEtp5HiNY7NfMoTpFEi7LGw" # Secondary
client = genai.Client(api_key=api_key)

try:
    for m in client.models.list():
        print(f"Model: {m.name}")
except Exception as e:
    print("Error:", e)
