import requests
import os
from bridge.config import AgentConfig, JouleConfig

print("BASE_URL:", os.getenv("AGENT_BASE_URL"))
print("TIMEOUT:", os.getenv("AGENT_TIMEOUT"))
print("PROVIDER:", os.getenv("AGENT_PROVIDER"))

# ── Shared call logic ─────────────────────────────────────────────────────────

def _call_agent(base_url: str, api_key: str, message: str,
                timeout: int, provider_name: str,
                skip_ngrok_warning: bool = False) -> str:
    """
    Shared HTTP call logic for any agent implementing the /chat contract.
    Contract: POST /chat  { "message": "..." }  →  { "reply": "..." }
    """
    if not base_url:
        return f"[{provider_name}] BASE_URL is not configured."

    headers = {"Content-Type": "application/json"}
    if skip_ngrok_warning:
        headers["ngrok-skip-browser-warning"] = "true"
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        response = requests.post(
            f"{base_url}/chat",
            json={"message": message},
            headers=headers,
            timeout=timeout
        )
        response.raise_for_status()
        data = response.json()

        return (
            data.get("reply")
            or data.get("response")
            or data.get("text")
            or data.get("answer")
            or data.get("output")
            or str(data)
        )

    except requests.exceptions.Timeout:
        return f"[{provider_name}] Request timed out after {timeout}s."
    except requests.exceptions.ConnectionError:
        return f"[{provider_name}] Could not connect to {base_url}. Is the agent running?"
    except requests.exceptions.HTTPError as e:
        return f"[{provider_name}] HTTP {e.response.status_code}: {e.response.text[:200]}"
    except Exception as e:
        return f"[{provider_name}] Unexpected error: {str(e)}"


# ── Eerly Studio adapter ──────────────────────────────────────────────────────

class AgentAdapter:
    """
    Adapter for Eerly AI Studio (or sandbox SAP Expert agent).
    Switch providers via AGENT_PROVIDER in .env:
      sandbox → local LangGraph agent (current)
      eerly   → real Eerly AI Studio API (future)
    """

    def __init__(self):
        self.provider = AgentConfig.PROVIDER
        self.base_url = AgentConfig.BASE_URL
        self.api_key  = AgentConfig.API_KEY
        self.timeout  = AgentConfig.REQUEST_TIMEOUT

    def chat(self, message: str) -> str:
        skip_ngrok = "ngrok" in (self.base_url or "")
        return _call_agent(
            base_url=self.base_url,
            api_key=self.api_key,
            message=message,
            timeout=self.timeout,
            provider_name=self.provider,
            skip_ngrok_warning=skip_ngrok
        )


# ── Joule adapter ─────────────────────────────────────────────────────────────

class JouleAdapter:
    """
    Adapter for SAP Joule (or Joule persona stand-in).
    To swap in real SAP Joule:
      1. Set JOULE_BASE_URL to real Joule endpoint URL
      2. Set JOULE_API_KEY to Joule API credentials
      3. Nothing else changes — same /chat contract
    """

    def __init__(self):
        self.base_url = JouleConfig.BASE_URL
        self.api_key  = JouleConfig.API_KEY
        self.timeout  = JouleConfig.REQUEST_TIMEOUT

    def chat(self, message: str) -> str:
        skip_ngrok = "ngrok" in (self.base_url or "")
        return _call_agent(
            base_url=self.base_url,
            api_key=self.api_key,
            message=message,
            timeout=self.timeout,
            provider_name="joule",
            skip_ngrok_warning=skip_ngrok
        )

# import requests
# from bridge.config import AgentConfig, JouleConfig

# class AgentAdapter:
#     """
#     Contract interface between the bridge and any agent provider.
#     Swap providers by changing AGENT_PROVIDER in .env — no code changes.
#     """

#     def __init__(self):
#         self.provider = AgentConfig.PROVIDER
#         self.base_url = AgentConfig.BASE_URL
#         self.timeout  = AgentConfig.REQUEST_TIMEOUT
#         self.headers  = self._build_headers()

#     def _build_headers(self) -> dict:
#         headers = {"Content-Type": "application/json"}

#         if self.provider == "sandbox":
#             # Sandbox (colleague's LangGraph app) — no auth needed locally
#             # ngrok requires this header to bypass its browser warning page
#             headers["ngrok-skip-browser-warning"] = "true"

#         elif self.provider == "eerly":
#             # Real Eerly AI Studio — Bearer token auth
#             headers["Authorization"] = f"Bearer {AgentConfig.API_KEY}"

#         return headers

#     def chat(self, message: str) -> str:
#         """
#         Send a message to the agent and return the reply as a string.
#         This is the only method the bridge app ever calls.
#         """
#         if not self.base_url:
#             raise ValueError("AGENT_BASE_URL is not set in .env")

#         endpoint = f"{self.base_url}/chat"

#         try:
#             response = requests.post(
#                 endpoint,
#                 json={"message": message},
#                 headers=self.headers,
#                 timeout=self.timeout
#             )
#             response.raise_for_status()
#             data = response.json()

#             # ── Response field normalisation ─────────────────────────────
#             # Sandbox and Eerly may use different field names.
#             # We try common ones in order and surface raw JSON if none match.
#             reply = (
#                 data.get("reply")
#                 or data.get("response")
#                 or data.get("text")
#                 or data.get("answer")
#                 or data.get("output")
#                 or str(data)
#             )
#             return reply

#         except requests.exceptions.Timeout:
#             return f"[{self.provider}] Request timed out after {self.timeout}s."
#         except requests.exceptions.ConnectionError:
#             return f"[{self.provider}] Could not connect to {endpoint}. Is the agent running?"
#         except requests.exceptions.HTTPError as e:
#             return f"[{self.provider}] HTTP error {e.response.status_code}: {e.response.text[:200]}"
#         except Exception as e:
#             return f"[{self.provider}] Unexpected error: {str(e)}"

