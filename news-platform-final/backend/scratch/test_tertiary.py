from google import genai

api_key = "AIzaSyArwJeb6Apc4Vq2_3-tCoEe3Q7ik6Kd_F8" # Tertiary
client = genai.Client(api_key=api_key)

try:
    for m in client.models.list():
        print(f"Model: {m.name}")
except Exception as e:
    print("Error:", e)
