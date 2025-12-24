import os
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("No API key")
    exit(1)

headers = {"Authorization": f"Bearer {api_key}"}

# 1. Try usage endpoint for today
today = datetime.now().strftime("%Y-%m-%d")
try:
    print(f"Checking usage for {today}...")
    resp = requests.get(f"https://api.openai.com/v1/usage?date={today}", headers=headers)
    if resp.status_code == 200:
        print("Usage Data:")
        print(resp.json())
    else:
        print(f"Usage index failed: {resp.status_code} - {resp.text}")
except Exception as e:
    print(f"Error checking usage: {e}")

# 2. Try subscription/billing if possible (often requires session key but worth a try)
endpoints = [
    "https://api.openai.com/v1/dashboard/billing/subscription",
    "https://api.openai.com/v1/dashboard/billing/credit_grants"
]

for url in endpoints:
    try:
        print(f"\nChecking {url.split('/')[-1]}...")
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            print(f"{url.split('/')[-1]} Data:")
            print(resp.json())
        else:
            print(f"Failed: {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")
