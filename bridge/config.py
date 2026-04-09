# from dotenv import load_dotenv
# import os

# load_dotenv()

# class AgentConfig:
#     PROVIDER         = os.getenv("AGENT_PROVIDER", "sandbox")
#     BASE_URL         = os.getenv("AGENT_BASE_URL")
#     API_KEY          = os.getenv("AGENT_API_KEY", "")
#     REQUEST_TIMEOUT  = int(os.getenv("AGENT_TIMEOUT", "30"))

from dotenv import load_dotenv
import os

load_dotenv()

class AgentConfig:
    PROVIDER         = os.getenv("AGENT_PROVIDER", "sandbox")
    BASE_URL         = os.getenv("AGENT_BASE_URL")
    API_KEY          = os.getenv("AGENT_API_KEY", "")
    REQUEST_TIMEOUT  = int(os.getenv("AGENT_TIMEOUT", "30"))

class JouleConfig:
    BASE_URL         = os.getenv("JOULE_BASE_URL", "http://localhost:8001")
    API_KEY          = os.getenv("JOULE_API_KEY", "")
    REQUEST_TIMEOUT  = int(os.getenv("AGENT_TIMEOUT", "30"))