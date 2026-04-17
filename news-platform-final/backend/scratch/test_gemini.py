import os
import logging
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_gemini")

api_key = "AIzaSyDweaZssdwJRDh7RSC1scmFvRMBtPwOtAY" # Primary from .env

def test():
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents="Hello, say test.",
        )
        print("Response:", response.text)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test()
