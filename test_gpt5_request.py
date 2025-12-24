import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    # Check if it was provided in another way or hardcode for test if absolutely necessary but let's stick to env
    exit(1)

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# Testing GPT-5.1
data_51 = {
    "model": "gpt-5.1",
    "messages": [{"role": "user", "content": "Hola, responde brevemente: ¿Tienes capacidad de 'thinking' o razonamiento profundo activa?"}],
    "max_completion_tokens": 100
}

try:
    print("Testing gpt-5.1...")
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data_51)
    response.raise_for_status()
    result = response.json()
    print("Response from gpt-5.1:")
    print(result["choices"][0]["message"]["content"])
except Exception as e:
    print(f"Error calling gpt-5.1: {e}")
    if hasattr(e, 'response') and e.response is not None:
        print(f"Details: {e.response.text}")

print("-" * 20)

# Testing o1-pro
data_o1 = {
    "model": "o1-pro",
    "messages": [{"role": "user", "content": "Hola, ¿estás disponible?"}],
    "max_completion_tokens": 100
}

try:
    print("Testing o1-pro...")
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data_o1)
    response.raise_for_status()
    result = response.json()
    print("Response from o1-pro:")
    print(result["choices"][0]["message"]["content"])
except Exception as e:
    print(f"Error calling o1-pro: {e}")
    if hasattr(e, 'response') and e.response is not None:
        print(f"Details: {e.response.text}")
