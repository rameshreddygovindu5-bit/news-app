
import os
from google import genai

keys = [
    "AIzaSyDweaZssdwJRDh7RSC1scmFvRMBtPwOtAY",
    "AIzaSyDOqGA7f69IcEtp5HiNY7NfMoTpFEi7LGw",
    "AIzaSyArwJeb6Apc4Vq2_3-tCoEe3Q7ik6Kd_F8"
]

for i, key in enumerate(keys):
    print(f"Testing Key {i+1}...")
    client = genai.Client(api_key=key)
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents="hi",
        )
        print(f"Key {i+1} OK")
    except Exception as e:
        print(f"Key {i+1} Error: {e}")
