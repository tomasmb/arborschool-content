import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("OPENAI_API_KEY not found in .env")
    exit(1)

headers = {
    "Authorization": f"Bearer {api_key}"
}

try:
    response = requests.get("https://api.openai.com/v1/models", headers=headers)
    response.raise_for_status()
    models = response.json()["data"]
    
    # Sort models by ID for easier reading
    model_ids = sorted([m["id"] for m in models])
    
    print("Available Models:")
    for mid in model_ids:
        if "o1" in mid or "gpt-5" in mid or "thinking" in mid:
            print(f"- {mid} (MATCH)")
        else:
            # Optionally print all or just a subset
            pass
            
    # Check specifically for o1-preview, o1-mini, or gpt-5 variations
    found_thinking = [mid for mid in model_ids if "o1" in mid or "gpt-5" in mid]
    if found_thinking:
        print("\nPotentially relevant models found:")
        for m in found_thinking:
            print(f"- {m}")
    else:
        print("\nNo 'o1' or 'gpt-5' models found in the list.")

except Exception as e:
    print(f"Error checking models: {e}")
