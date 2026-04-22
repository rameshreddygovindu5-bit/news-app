
import os
from google import genai
from google.genai import types

api_key = "AIzaSyDweaZssdwJRDh7RSC1scmFvRMBtPwOtAY" # from .env

client = genai.Client(api_key=api_key)
try:
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents="Hello, can you hear me?",
    )
    print("Response:", response.text)
except Exception as e:
    print("Error:", e)
