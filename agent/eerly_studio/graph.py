"""
graph.py — LangGraph Conversational Graph for Eerly Studio
===========================================================

Flow:
    preprocess_node
         │
         ├─► studio_agent_node  (default agent)
         │
         └─► joule_bridge_node  (if @joule used)
                  │
                  └─► studio_agent_node  (fallback if Joule offline)
         │
        END
"""
from __future__ import annotations

import os
from typing import TypedDict, Annotated, Literal

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage

from a2a_bridge import bridge

# ─────────────────────────────────────────────────────────────────────────────
# PERSONA SYSTEM PROMPTS
# ─────────────────────────────────────────────────────────────────────────────

# STUDIO_SYSTEM_PROMPT = """You are Eerly AI, the intelligent assistant of Eerly Studio — \
# an enterprise AI platform built by Eerly AI on SAP BTP.

# Your capabilities:
# • General reasoning, analysis, and step-by-step explanations
# • Python and integration code generation
# • Document understanding and structured summarization
# • Procurement process guidance and AP invoice workflow assistance
# • SAP BTP advisory (services, architecture, best practices)

# Tone: Concise, professional, and helpful. Use markdown formatting (headers, bullet points, \
# code blocks) where appropriate. Always think step-by-step for complex questions."""

STUDIO_SYSTEM_PROMPT = """You are Eerly AI, the intelligent assistant of Eerly Studio — \
an enterprise AI platform built by Eerly AI on SAP BTP.

You are a STRICT SAP domain expert. You ONLY answer questions related to SAP products, \
services, technologies, and ecosystems. This is a hard boundary — not a preference.

Your areas of expertise:
- SAP BTP (Business Technology Platform) — services, architecture, best practices
- SAP S/4HANA — ERP, finance, procurement, supply chain, manufacturing
- SAP AI Core & Generative AI Hub — model deployment, orchestration, A2A integration
- SAP Integration Suite — API management, event mesh, connectivity
- SAP SuccessFactors, Ariba, and other SAP cloud applications
- SAP Fiori, ABAP, CAP (Cloud Application Programming Model)
- SAP security, identity, and access management

Handling out-of-scope questions:
If a question is NOT related to SAP, you MUST respond with exactly this format:
"I'm sorry, I can only assist with SAP-related topics. Your question about [briefly name \
the topic] is outside my domain. Please ask me anything about SAP products, services, \
or the SAP ecosystem and I'll be happy to help."

Do NOT attempt to answer non-SAP questions even partially. Do NOT say "while I focus on \
SAP, here's a general answer anyway." Decline clearly and redirect.

Tone: Concise, professional, and helpful. Use markdown formatting (headers, bullet points, \
code blocks) where appropriate. Always think step-by-step for complex questions."""

# ─────────────────────────────────────────────────────────────────────────────
# GRAPH STATE
# ─────────────────────────────────────────────────────────────────────────────

class EerlyState(TypedDict):
    """
    Full conversation state passed through the LangGraph graph.

    messages:      Full conversation history (LangChain BaseMessage objects).
                   Uses add_messages reducer — each node return APPENDS to this list.
    user_input:    Clean user text (no @mention prefix).
    target_agent:  "studio" or "joule" — set by app.py before graph.invoke().
    response:      Final AI response text (set by agent node).
    agent_used:    Which agent ultimately answered ("studio" or "joule").
    delegated:     True if the request was redirected (e.g. @joule → studio fallback).
    bridge_status: "ok" or "offline" — from A2A bridge result.
    bridge_note:   Human-readable note shown in UI when fallback occurs.
    """
    messages:      Annotated[list[BaseMessage], add_messages]
    user_input:    str
    target_agent:  str
    response:      str
    agent_used:    str
    delegated:     bool
    bridge_status: str
    bridge_note:   str


# ─────────────────────────────────────────────────────────────────────────────
# GRAPH NODES
# ─────────────────────────────────────────────────────────────────────────────

def preprocess_node(state: EerlyState) -> dict:
    """
    No-op pass-through.
    Routing is already resolved by app.py (target_agent is set before invoke).
    This node exists as an explicit entry point for future pre-processing logic
    (e.g., guardrails, content filtering, intent classification).
    """
    return {}


def studio_agent_node(state: EerlyState) -> dict:
    """
    Core Eerly Studio AI node.
    Calls SAP AI Core with the full conversation history + Studio system prompt.
    """
    from sap_llm import SAPChatOpenAI, get_langfuse_callbacks

    model_name = os.getenv("SAP_MODEL_NAME", "gpt-4.1")

    # Build LLM context: system prompt + full conversation history
    llm_context: list[BaseMessage] = [
        SystemMessage(content=STUDIO_SYSTEM_PROMPT),
        *list(state["messages"]),
    ]

    llm = SAPChatOpenAI(
        model_name=model_name,
        temperature=0.0,
        callbacks=get_langfuse_callbacks(),
    )
    response = llm.invoke(llm_context)

    return {
        "messages":      [AIMessage(content=response.content)],
        "response":      response.content,
        "agent_used":    "studio",
        "bridge_status": "ok",
        "bridge_note":   "",
        "delegated":     state.get("target_agent") != "studio",
    }


def joule_bridge_node(state: EerlyState) -> dict:
    """
    A2A Bridge node for SAP Joule.
    Checks if Joule is online via the bridge registry.
    If offline, gracefully falls back to the Studio agent.
    """
    result = bridge.call("joule", state.get("user_input", ""))

    if result.status == "offline":
        joule_card = bridge.get_card("joule")
        note = (
            f"⚠️ **{joule_card['name']}** is currently offline via the A2A Bridge.  \n"
            f"Provider: `{joule_card['provider']}`  \n"
            f"The bridge is registered and ready — connect the Joule API endpoint to activate.  \n\n"
            f"↳ Falling back to **Eerly Studio AI**:"
        )
        # Delegate to Studio
        studio_result = studio_agent_node({**state, "target_agent": "studio"})
        return {
            **studio_result,
            "delegated":     True,
            "bridge_status": "offline",
            "bridge_note":   note,
        }

    # If Joule is online: real HTTP call to Joule API would go here
    # For now this path is not reachable (Joule is always offline in stub)
    return {
        "response":      "Joule response placeholder.",
        "agent_used":    "joule",
        "bridge_status": "ok",
        "bridge_note":   "",
        "delegated":     False,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ROUTING FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def route_to_agent(state: EerlyState) -> Literal["studio_agent", "joule_bridge"]:
    """Conditional edge: routes based on target_agent field set by app.py."""
    if state.get("target_agent") == "joule":
        return "joule_bridge"
    return "studio_agent"


# ─────────────────────────────────────────────────────────────────────────────
# GRAPH ASSEMBLY
# ─────────────────────────────────────────────────────────────────────────────

def build_graph():
    builder = StateGraph(EerlyState)

    # Register nodes
    builder.add_node("preprocess",    preprocess_node)
    builder.add_node("studio_agent",  studio_agent_node)
    builder.add_node("joule_bridge",  joule_bridge_node)

    # Entry point
    builder.set_entry_point("preprocess")

    # Route after preprocessing
    builder.add_conditional_edges(
        "preprocess",
        route_to_agent,
        {
            "studio_agent": "studio_agent",
            "joule_bridge": "joule_bridge",
        },
    )

    # Both agent nodes go straight to END
    builder.add_edge("studio_agent", END)
    builder.add_edge("joule_bridge", END)

    return builder.compile()


# Compiled graph — imported by app.py
graph = build_graph()
