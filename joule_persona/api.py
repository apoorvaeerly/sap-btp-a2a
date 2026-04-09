"""
api.py — FastAPI REST wrapper for SAP Joule persona agent
==========================================================
Exposes POST /chat on port 8001 using the same contract as Eerly Studio:
  Request:  { "message": "..." }
  Response: { "reply": "...", "agent_used": "joule", ... }

When real SAP Joule API becomes available:
  1. Replace graph.invoke() call below with HTTP POST to real Joule endpoint
  2. Map Joule's response fields to this contract shape
  3. Update AGENT_PROVIDER=joule in .env
  4. Nothing else in the bridge or tests changes

Run with:
  uvicorn joule_persona.api:app --port 8001 --reload
"""
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, ".."))

# .env lives at project root
from dotenv import load_dotenv
load_dotenv(os.path.join(_root, ".env"))

# Make eerly_studio/ importable for sap_llm.py
_eerly = os.path.join(_root, "agent", "eerly_studio")
if _eerly not in sys.path:
    sys.path.insert(0, _eerly)

# Make joule_persona/ importable for graph.py + prompts.py
if _here not in sys.path:
    sys.path.insert(0, _here)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from graph import graph, JouleState

app = FastAPI(
    title="SAP Joule Persona API",
    description=(
        "Stand-in for SAP Joule. Implements the same A2A /chat contract "
        "as Eerly Studio. Swap for real Joule by updating the endpoint URL."
    ),
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Models ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply:      str
    agent_used: str = "joule"
    status:     str = "ok"
    note:       str = ""

# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status":    "ok",
        "service":   "joule-persona-api",
        "note":      "Stand-in for SAP Joule. Replace endpoint URL for real Joule."
    }

# ── Chat ──────────────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message field is required")

    try:
        result: JouleState = graph.invoke({
            "messages":   [HumanMessage(content=req.message.strip())],
            "user_input": req.message.strip(),
            "response":   "",
        })

        return ChatResponse(
            reply=result.get("response", ""),
            agent_used="joule",
            status="ok",
            note="Served by Joule persona stand-in via SAP AI Core GPT-4.1"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))