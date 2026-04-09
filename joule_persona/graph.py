"""
graph.py — LangGraph graph for SAP Joule persona agent
=======================================================
Intentionally simple — single node, no routing.
Joule persona has no @mention routing logic (that lives in Eerly Studio).
When real Joule API is available, this entire file is replaced by a direct
HTTP call to the Joule endpoint in api.py.
"""
from __future__ import annotations

import os
import sys
from typing import TypedDict, Annotated

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage

from prompts import JOULE_SYSTEM_PROMPT

# ── Ensure sap_llm.py is importable from eerly_studio/ ───────────────────────
_here = os.path.dirname(os.path.abspath(__file__))
_eerly = os.path.abspath(os.path.join(_here, "..", "agent", "eerly_studio"))
if _eerly not in sys.path:
    sys.path.insert(0, _eerly)


# ── State ─────────────────────────────────────────────────────────────────────

class JouleState(TypedDict):
    messages:  Annotated[list[BaseMessage], add_messages]
    user_input: str
    response:   str


# ── Node ──────────────────────────────────────────────────────────────────────

def joule_agent_node(state: JouleState) -> dict:
    """
    Single node — calls SAP AI Core with Joule persona system prompt.
    Reuses sap_llm.py from eerly_studio/ — same AI Core deployment,
    different persona.
    """
    from sap_llm import SAPChatOpenAI, get_langfuse_callbacks

    model_name = os.getenv("SAP_MODEL_NAME", "gpt-4.1")

    llm_context: list[BaseMessage] = [
        SystemMessage(content=JOULE_SYSTEM_PROMPT),
        *list(state["messages"]),
    ]

    llm = SAPChatOpenAI(
        model_name=model_name,
        temperature=0.0,
        callbacks=get_langfuse_callbacks(),
    )
    response = llm.invoke(llm_context)

    return {
        "messages": [AIMessage(content=response.content)],
        "response": response.content,
    }


# ── Graph assembly ────────────────────────────────────────────────────────────

def build_graph():
    builder = StateGraph(JouleState)
    builder.add_node("joule_agent", joule_agent_node)
    builder.set_entry_point("joule_agent")
    builder.add_edge("joule_agent", END)
    return builder.compile()


graph = build_graph()