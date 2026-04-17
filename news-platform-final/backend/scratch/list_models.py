from google import genai

api_key = "AIzaSyDweaZssdwJRDh7RSC1scmFvRMBtPwOtAY"
client = genai.Client(api_key=api_key)

try:
    for m in client.models.list():
        print(f"Model: {m.name}, Methods: {m.supported_methods}")
except Exception as e:
    print("Error:", e)
