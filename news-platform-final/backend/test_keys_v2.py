
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
        # Try different model name variations
        for model_name in ["gemini-1.5-flash", "models/gemini-1.5-flash", "gemini-pro"]:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents="hi",
                )
                print(f"Key {i+1} OK with {model_name}")
                break
            except Exception as e:
                print(f"Key {i+1} failed with {model_name}: {e}")
    except Exception as e:
        print(f"Key {i+1} Error: {e}")
