"""
a2a_bridge.py — Agent-to-Agent (A2A) Bridge
Based on the Google A2A protocol concept: https://google.github.io/A2A/

Each agent is described by an AgentCard (capability manifest).
The bridge maintains a registry and routes messages to online agents.
Offline agents degrade gracefully with a fallback message.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# AGENT CARDS
# In the full A2A spec, these are served at /.well-known/agent.json
# ─────────────────────────────────────────────────────────────────────────────

EERLY_STUDIO_CARD: dict = {
    "name":        "Eerly Studio AI",
    "handle":      "@studio",
    "description": (
        "Enterprise AI assistant built by Accely Solutions DMCC on SAP BTP. "
        "Specializes in reasoning, code generation, document analysis, "
        "procurement advisory, and AP invoice workflows."
    ),
    "icon":        "🏢",
    "version":     "1.0.0",
    "url":         "http://localhost:8501",
    "provider":    "SAP AI Core — GPT-4.1",
    "status":      "online",
    "capabilities": {
        "streaming":         False,
        "pushNotifications": False,
        "multiTurn":         True,
    },
    "skills": [
        {"id": "general_qa",       "name": "General Reasoning & Q&A",     "available": True},
        {"id": "code_gen",         "name": "Code Generation",              "available": True},
        {"id": "doc_analysis",     "name": "Document Analysis",            "available": True},
        {"id": "procurement",      "name": "Procurement & AP Workflows",   "available": True},
        {"id": "sap_integration",  "name": "SAP Integration Advisory",     "available": True},
    ],
}

JOULE_CARD: dict = {
    "name":        "SAP Joule",
    "handle":      "@joule",
    "description": (
        "SAP's official AI copilot embedded across the SAP enterprise application suite. "
        "Specializes in SAP BTP lifecycle, S/4HANA, SuccessFactors, Ariba, and "
        "SAP Integration Suite."
    ),
    "icon":        "💼",
    "version":     "stub-1.0",
    "url":         None,          # No public API endpoint yet
    "provider":    "SAP SE (Joule API — pending availability)",
    "status":      "offline",     # Flip to "online" when real API is ready
    "capabilities": {
        "streaming":         False,
        "pushNotifications": False,
        "multiTurn":         True,
    },
    "skills": [
        {"id": "btp_mgmt",     "name": "SAP BTP Management",        "available": False},
        {"id": "s4hana",       "name": "S/4HANA Guidance",           "available": False},
        {"id": "successfactors","name": "SuccessFactors HR",          "available": False},
        {"id": "ariba",        "name": "SAP Ariba Procurement",      "available": False},
        {"id": "integration",  "name": "SAP Integration Suite",      "available": False},
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# A2A BRIDGE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BridgeResult:
    status:   str            # "ok" | "offline" | "error"
    agent:    str            # agent key that was called
    content:  Optional[str]  # Response text (None if offline)
    fallback: bool = False   # Was a fallback triggered?
    error:    Optional[str] = None


class A2ABridge:
    """
    Maintains a registry of Agent Cards.
    Routes messages to registered agents and handles failures gracefully.

    To add a new agent:
        bridge.register("my_agent", MY_AGENT_CARD)

    To bring Joule online:
        bridge.registry["joule"]["status"] = "online"
        bridge.registry["joule"]["url"]    = "https://your-joule-endpoint"
    """

    def __init__(self):
        self.registry: dict[str, dict] = {
            "studio": EERLY_STUDIO_CARD,
            "joule":  JOULE_CARD,
        }

    def register(self, key: str, card: dict) -> None:
        """Register a new agent in the bridge."""
        self.registry[key] = card

    def get_card(self, agent_key: str) -> dict:
        return self.registry.get(agent_key, {})

    def is_online(self, agent_key: str) -> bool:
        return self.registry.get(agent_key, {}).get("status") == "online"

    def list_agents(self) -> list[dict]:
        """Return all registered agent cards."""
        return list(self.registry.values())

    def call(self, agent_key: str, message: str) -> BridgeResult:
        """
        Attempt to call an agent via the bridge.

        Returns a BridgeResult indicating success or offline status.
        Actual LLM invocation for 'studio' happens in the LangGraph node —
        this bridge only handles routing decisions and offline checks.
        """
        card = self.get_card(agent_key)
        if not card:
            return BridgeResult(
                status="error",
                agent=agent_key,
                content=None,
                error=f"Agent '{agent_key}' not registered in A2A bridge.",
            )

        if not self.is_online(agent_key):
            return BridgeResult(
                status="offline",
                agent=agent_key,
                content=None,
                fallback=True,
                error=f"{card['name']} is offline. API endpoint not yet available.",
            )

        # If the agent is "studio", the LangGraph node handles the actual LLM call.
        # For future real agents (Joule with a real URL), we'd POST to card["url"] here.
        return BridgeResult(status="ok", agent=agent_key, content=None)


# Module-level singleton — imported by graph.py and app.py
bridge = A2ABridge()
