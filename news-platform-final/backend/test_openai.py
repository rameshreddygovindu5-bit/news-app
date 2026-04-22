
import os
from openai import OpenAI

# from .env
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)
try:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "hi"}]
    )
    print("Response:", response.choices[0].message.content)
except Exception as e:
    print("Error:", e)
