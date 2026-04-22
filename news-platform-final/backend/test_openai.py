
import os
from openai import OpenAI

# from .env
api_key = "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"

client = OpenAI(api_key=api_key)
try:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "hi"}]
    )
    print("Response:", response.choices[0].message.content)
except Exception as e:
    print("Error:", e)
