import requests
from dotenv import load_dotenv
import os

load_dotenv()

AUTH_URL = os.getenv("AI_CORE_AUTH_URL")
CLIENT_ID = os.getenv("AI_CORE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AI_CORE_CLIENT_SECRET")

response = requests.post(
    AUTH_URL,
    data={"grant_type": "client_credentials"},
    auth=(CLIENT_ID, CLIENT_SECRET)
)

print("Status code:", response.status_code)
print("Response:", response.json())