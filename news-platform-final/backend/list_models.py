
import os
from google import genai

api_key = "AIzaSyDweaZssdwJRDh7RSC1scmFvRMBtPwOtAY"
client = genai.Client(api_key=api_key)

try:
    for model in client.models.list():
        print(model.name, model.supported_methods)
except Exception as e:
    print("Error:", e)
