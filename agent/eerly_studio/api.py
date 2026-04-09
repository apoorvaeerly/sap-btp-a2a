"""
api.py — FastAPI REST wrapper for Eerly Studio LangGraph agent.
Exposes POST /chat so the A2A bridge adapter can call it.
Run with: uvicorn eerly_studio.api:app --port 8000 --reload
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
# load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
# Explicitly walk up to find .env at project root
_here = os.path.dirname(os.path.abspath(__file__))          # agent/eerly_studio/
_root = os.path.abspath(os.path.join(_here, "..", ".."))    # sap-btp-a2a/
load_dotenv(os.path.join(_root, ".env"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from graph import graph, EerlyState

app = FastAPI(
    title="Eerly Studio A2A API",
    description="REST interface for the Eerly Studio LangGraph agent",
    version="1.0.0"
)

# Allow ngrok + bridge app to call this
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request / Response models ─────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str
    agent_used: str
    bridge_status: str
    bridge_note: str

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "eerly-studio-api"}

# ── Chat endpoint ─────────────────────────────────────────────────────────────
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message field is required")

    try:
        result: EerlyState = graph.invoke({
            "messages":      [HumanMessage(content=req.message.strip())],
            "user_input":    req.message.strip(),
            "target_agent":  "studio",
            "response":      "",
            "agent_used":    "studio",
            "delegated":     False,
            "bridge_status": "ok",
            "bridge_note":   "",
        })

        return ChatResponse(
            reply=result.get("response", ""),
            agent_used=result.get("agent_used", "studio"),
            bridge_status=result.get("bridge_status", "ok"),
            bridge_note=result.get("bridge_note", ""),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))