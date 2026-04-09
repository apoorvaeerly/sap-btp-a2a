"""
sap_llm.py — SAP AI Core LLM Adapter
Reused from chat.py — standalone, no external dependencies.
"""
import os
import requests
from langchain_openai import ChatOpenAI


class SAPChatOpenAI(ChatOpenAI):
    """LangChain-compatible Chat model for SAP Generative AI Hub."""

    def __init__(self, model_name: str = "gpt-4.1", **kwargs):
        client_id      = os.getenv("AI_CORE_CLIENT_ID")
        client_secret  = os.getenv("AI_CORE_CLIENT_SECRET")
        auth_url       = os.getenv("AI_CORE_AUTH_URL")
        api_url        = os.getenv("AI_CORE_API_URL")
        resource_group = os.getenv("AI_CORE_RESOURCE_GROUP", "default")

        if not all([client_id, client_secret, auth_url, api_url]):
            raise ValueError(
                "SAP AI Core credentials missing. "
                "Set AI_CORE_CLIENT_ID, AI_CORE_CLIENT_SECRET, "
                "AI_CORE_AUTH_URL, AI_CORE_API_URL in .env"
            )

        # 1. Fetch OAuth2 token
        token_resp = requests.post(
            auth_url,
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            timeout=15,
        )
        token_resp.raise_for_status()
        token = token_resp.json()["access_token"]

        # 2. Discover active deployment for the requested model
        headers = {
            "Authorization":   f"Bearer {token}",
            "AI-Resource-Group": resource_group,
        }
        deploy_resp = requests.get(
            f"{api_url}/v2/lm/deployments",
            headers=headers,
            timeout=15,
        )
        deploy_resp.raise_for_status()
        deployments = deploy_resp.json().get("resources", [])

        deployment_url = None
        for d in deployments:
            if d.get("status") != "RUNNING":
                continue
            try:
                actual_model = d["details"]["resources"]["backend_details"]["model"]["name"]
            except (KeyError, TypeError):
                actual_model = d.get("modelName", d.get("configurationName", ""))
            if actual_model and model_name in actual_model:
                deployment_url = d.get("deploymentUrl")
                break

        if not deployment_url:
            running = []
            for d in deployments:
                if d.get("status") == "RUNNING":
                    try:
                        running.append(
                            d["details"]["resources"]["backend_details"]["model"]["name"]
                        )
                    except (KeyError, TypeError):
                        running.append(d.get("configurationName", "Unknown"))
            raise RuntimeError(
                f"No RUNNING deployment found for model '{model_name}'. "
                f"Available: {running}"
            )

        super().__init__(
            model=model_name,
            api_key=token,
            base_url=deployment_url,
            default_headers={"AI-Resource-Group": resource_group},
            model_kwargs={"extra_query": {"api-version": "2024-02-15-preview"}},
            **kwargs,
        )


def get_langfuse_callbacks():
    """Return Langfuse callback handler if configured, else None.
    Langfuse SDK automatically reads LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY,
    and LANGFUSE_HOST from environment variables — no kwargs needed.
    """
    if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
        try:
            from langfuse.langchain import CallbackHandler
            return [CallbackHandler()]
        except ImportError:
            pass
    return None
