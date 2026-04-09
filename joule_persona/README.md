# Joule Persona — SAP Joule Stand-in Agent

This module is a **stand-in for SAP Joule** — SAP's official AI copilot. It implements the same A2A contract interface (`POST /chat`) as Eerly Studio, powered by SAP AI Core GPT-4.1 with a SAP Joule system prompt.

When real SAP Joule becomes available (via SuccessFactors, SAP Build Work Zone, or S/4HANA), this module is retired and replaced by updating a single URL in `.env`. No other changes are needed anywhere in the codebase.

---

## What This Module Does

- Exposes a `POST /chat` REST endpoint (FastAPI) on **port 8001**
- Responds as SAP Joule — authoritative SAP product knowledge, SAP's own voice
- Rejects non-SAP questions with a Joule-branded message
- Acknowledges Eerly AI Studio as a registered A2A partner agent
- Reuses `sap_llm.py` from `agent/eerly_studio/` — no duplication of AI Core logic

---

## File Reference

| File | Purpose |
|---|---|
| `api.py` | FastAPI app — exposes `GET /health` and `POST /chat` on port 8001 |
| `graph.py` | LangGraph graph — single node with Joule persona system prompt |
| `prompts.py` | Joule system prompt — the only file that changes when real Joule arrives |
| `__init__.py` | Makes this a Python package for clean imports |

---

## Prerequisites

- Eerly Studio agent running on port 8000 (shares the same `.env` and `sap_llm.py`)
- `.env` file configured at project root
- Same virtual environment as the rest of the project

---

## Installation

Dependencies are shared with Eerly Studio. If you have already installed Eerly Studio dependencies, nothing additional is needed:

```bash
pip install -r agent/eerly_studio/requirements.txt
pip install fastapi uvicorn
```

---

## Starting the Agent

Always run from the **project root** (`sap-btp-a2a/`):

```bash
uvicorn joule_persona.api:app --port 8001 --reload
```

Expected output:

```
INFO:     Uvicorn running on http://127.0.0.1:8001
INFO:     Application startup complete.
```

Note: Port 8001 is used deliberately so both agents can run simultaneously alongside the Eerly Studio agent on port 8000.

---

## API Reference

### Health check

```http
GET http://localhost:8001/health
```

Response:

```json
{
  "status": "ok",
  "service": "joule-persona-api",
  "note": "Stand-in for SAP Joule. Replace endpoint URL for real Joule."
}
```

### Chat endpoint

```http
POST http://localhost:8001/chat
Content-Type: application/json

{
  "message": "What is SAP S/4HANA?"
}
```

Response:

```json
{
  "reply": "SAP S/4HANA is SAP's next-generation ERP suite...",
  "agent_used": "joule",
  "status": "ok",
  "note": "Served by Joule persona stand-in via SAP AI Core GPT-4.1"
}
```

### Quick test

```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"What is SAP SuccessFactors?\"}"
```

---

## SAP Joule Persona

The system prompt is defined in `prompts.py` under `JOULE_SYSTEM_PROMPT`. Key behaviours:

- **Voice:** Authoritative, precise — speaks as SAP itself, not as a third-party tool
- **Answers:** SAP S/4HANA, BTP, SuccessFactors, Ariba, Integration Suite, Build, Fiori, AI Core, ABAP, IAS
- **Rejects:** Non-SAP questions with: *"I'm SAP Joule and I specialise in SAP's product ecosystem..."*
- **Eerly awareness:** When asked about Eerly AI Studio, acknowledges it as a registered A2A partner agent

### Difference between Eerly and Joule personas

| Aspect | Eerly Studio | Joule persona |
|---|---|---|
| Voice | Third-party enterprise AI on SAP BTP | SAP's own official copilot |
| Rejection message | "I can only assist with SAP-related topics" | "I'm SAP Joule and I specialise in SAP's ecosystem" |
| Eerly awareness | N/A | Acknowledges Eerly as an A2A partner |
| Port | 8000 | 8001 |
| `agent_used` field | `studio` | `joule` |

---

## LangGraph Flow

```
User message
     │
     ▼
joule_agent_node
     │  system prompt: JOULE_SYSTEM_PROMPT (from prompts.py)
     │  calls SAP AI Core via sap_llm.py
     │  same GPT-4.1 deployment as Eerly Studio
     ▼
    END
```

The Joule graph is intentionally simpler than the Eerly graph — single node, no routing. Routing logic (`@joule`, `@eerly` mentions) lives in Eerly Studio's `app.py`.

---

## How sap_llm.py Is Shared

`graph.py` adds the `eerly_studio/` path to `sys.path` at runtime:

```python
_eerly = os.path.abspath(os.path.join(_here, "..", "agent", "eerly_studio"))
sys.path.insert(0, _eerly)

from sap_llm import SAPChatOpenAI, get_langfuse_callbacks
```

This means both agents share the same AI Core adapter with no code duplication. Both use the same OAuth token flow, deployment discovery, and resource group configuration.

---

## Environment Variables

These are read from the `.env` file at project root — same as Eerly Studio:

| Variable | Required | Description |
|---|---|---|
| `AI_CORE_CLIENT_ID` | Yes | SAP AI Core client ID |
| `AI_CORE_CLIENT_SECRET` | Yes | SAP AI Core client secret |
| `AI_CORE_AUTH_URL` | Yes | OAuth token URL |
| `AI_CORE_API_URL` | Yes | AI API base URL |
| `AI_CORE_RESOURCE_GROUP` | No | Defaults to `default` |
| `SAP_MODEL_NAME` | No | Defaults to `gpt-4.1` |
| `JOULE_BASE_URL` | No | Used by bridge adapter. Defaults to `http://localhost:8001` |
| `JOULE_API_KEY` | No | Leave empty for persona stand-in |

---

## Replacing This Module With Real SAP Joule

This is the most important section of this README. When real SAP Joule is available, this is the exact sequence to follow.

### Option A — SuccessFactors Joule via HTTP skill

**Prerequisites:**
- SF Joule instance with HTTP skill extensibility enabled (confirm with SF admin)
- CF bridge app deployed with a permanent public URL (see `bridge/README.md`)

**Steps:**

1. Register the CF bridge app URL as an HTTP skill in SF Joule Admin
2. Update `.env` at project root:

```dotenv
JOULE_BASE_URL=https://your-cf-bridge-app.cfapps.us10.hana.ondemand.com
JOULE_API_KEY=your-sf-joule-credentials
```

3. In `api.py`, replace the `graph.invoke()` block with a direct HTTP call:

```python
import requests

response = requests.post(
    f"{os.getenv('JOULE_BASE_URL')}/chat",
    json={"message": req.message},
    headers={"Authorization": f"Bearer {os.getenv('JOULE_API_KEY')}"},
    timeout=30
)
data = response.json()
return ChatResponse(
    reply=data.get("reply") or data.get("response", ""),
    agent_used="joule",
    status="ok"
)
```

4. Verify:

```bash
python bridge/test_adapter.py
python tests/test_e2e.py
```

### Option B — SAP Build Work Zone

1. Subscribe to SAP Build Work Zone in BTP subaccount
2. Register `@Eerly` as HTTP Action skill pointing to CF bridge app
3. Update `JOULE_BASE_URL` to the SAP Build endpoint
4. Same verification steps as Option A

### Option C — S/4HANA Joule (production)

See `docs/joule_enablement.md` for the full implementation guide.

---

## Running Both Agents Simultaneously

For the full A2A demo, both agents must be running at the same time in separate terminal windows:

**Window 1:**
```bash
uvicorn agent.eerly_studio.api:app --port 8000 --reload
```

**Window 2:**
```bash
uvicorn joule_persona.api:app --port 8001 --reload
```

**Window 3:**
```bash
ngrok\ngrok.exe http 8000
```

**Window 4 (testing):**
```bash
python tests/test_e2e.py
```

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'sap_llm'`

The `sap_llm.py` path resolution failed. This happens when uvicorn is not run from the project root. Always run from `sap-btp-a2a/`:

```bash
cd sap-btp-a2a
uvicorn joule_persona.api:app --port 8001 --reload
```

### Port 8001 already in use

```bash
# Windows
netstat -ano | findstr :8001
taskkill /PID <pid> /F
```

### Responses sound like Eerly, not Joule

The `JOULE_SYSTEM_PROMPT` in `prompts.py` may not be loading. Add a quick debug print in `graph.py`:

```python
print("Using prompt:", JOULE_SYSTEM_PROMPT[:100])
```

Restart uvicorn and check the terminal output.