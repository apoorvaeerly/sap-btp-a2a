import requests
from dotenv import load_dotenv
import os

load_dotenv()
# Point explicitly to your .env file location
# load_dotenv(dotenv_path=r"D:\SAP_BTP\SAP_BTP_v2\.env")

print("Deployment ID:", os.getenv("AI_CORE_DEPLOYMENT_ID"))
print("API URL:", os.getenv("AI_CORE_API_URL"))

AUTH_URL = os.getenv("AI_CORE_AUTH_URL")
CLIENT_ID = os.getenv("AI_CORE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AI_CORE_CLIENT_SECRET")
API_URL = os.getenv("AI_CORE_API_URL")
DEPLOYMENT_ID = os.getenv("AI_CORE_DEPLOYMENT_ID")
RESOURCE_GROUP = os.getenv("AI_CORE_RESOURCE_GROUP", "default")


# print("Endpoint:", endpoint)
# print("Resource Group:", RESOURCE_GROUP)
# Step 1 — get token
token_response = requests.post(
    AUTH_URL,
    data={"grant_type": "client_credentials"},
    auth=(CLIENT_ID, CLIENT_SECRET)
)
token = token_response.json()["access_token"]
print("Token acquired successfully")

# Step 2 — call completions
# endpoint = f"{API_URL}/v2/inference/deployments/{DEPLOYMENT_ID}/chat/completions"
endpoint = f"{API_URL}/v2/inference/deployments/{DEPLOYMENT_ID}/chat/completions?api-version=2024-02-01"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "AI-Resource-Group": RESOURCE_GROUP
}

payload = {
    "messages": [
        {
            "role": "user",
            "content": "In one sentence, what is SAP AI Core?"
        }
    ],
    "max_tokens": 100
}
print("Endpoint:", endpoint)
print("Resource Group:", RESOURCE_GROUP)
response = requests.post(endpoint, headers=headers, json=payload)

print("Status code:", response.status_code)
print("Response:", response.json())