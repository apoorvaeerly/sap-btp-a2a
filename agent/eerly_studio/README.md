# Eerly Studio — SAP Expert Agent

This module is the **Eerly AI Studio proxy agent** — a LangGraph-based conversational AI running on SAP AI Core (GPT-4.1). It acts as a stand-in for the full Eerly AI Studio platform during the A2A sandbox demo, and is designed to be replaced by the real Eerly AI Studio API with a single configuration change.

---

## What This Module Does

- Exposes a `POST /chat` REST endpoint (FastAPI) on **port 8000**
- Answers SAP-related questions using a strict SAP Expert persona
- Rejects non-SAP questions with a clear domain boundary message
- Provides a Streamlit UI with `@joule` mention routing via the A2A bridge
- Uses SAP AI Core GPT-4.1 as the LLM backend via `sap_llm.py`

---

## File Reference

| File | Purpose |
|---|---|
| `api.py` | FastAPI app — exposes `GET /health` and `POST /chat` on port 8000 |
| `app.py` | Streamlit UI — chat interface with `@joule` mention routing |
| `graph.py` | LangGraph graph — SAP Expert persona, preprocess + agent nodes |
| `a2a_bridge.py` | Agent registry — routes `@joule` and `@studio` mentions |
| `sap_llm.py` | SAP AI Core LLM adapter — handles OAuth + deployment discovery |
| `requirements.txt` | Python dependencies |

---

## Prerequisites

- Python 3.11+
- Virtual environment activated
- `.env` file configured at project root (see [Environment Variables](#environment-variables))
- SAP AI Core credentials validated (`python tests/test_token_at.py`)

---

## Installation

Run from the **project root** (`sap-btp-a2a/`):

```bash
pip install -r agent/eerly_studio/requirements.txt
pip install fastapi uvicorn
```

---

## Starting the Agent

Always run from the **project root**, not from inside the folder:

```bash
# From sap-btp-a2a/
uvicorn agent.eerly_studio.api:app --port 8000 --reload
```

Expected output:

```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

---

## API Reference

### Health check

```http
GET http://localhost:8000/health
```

Response:

```json
{
  "status": "ok",
  "service": "eerly-studio-api"
}
```

### Chat endpoint

```http
POST http://localhost:8000/chat
Content-Type: application/json

{
  "message": "What is SAP BTP?"
}
```

Response:

```json
{
  "reply": "SAP BTP (Business Technology Platform) is...",
  "agent_used": "studio",
  "bridge_status": "ok",
  "bridge_note": ""
}
```

### Quick test

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"What is SAP AI Core?\"}"
```

---

## SAP Expert Persona

The agent's system prompt is defined in `graph.py` under `STUDIO_SYSTEM_PROMPT`. Key behaviours:

- **Answers:** Any question about SAP products, services, BTP, S/4HANA, AI Core, Integration Suite, Fiori, ABAP, CAP, SuccessFactors, Ariba
- **Rejects:** Any non-SAP question with: *"I'm sorry, I can only assist with SAP-related topics..."*
- **Tone:** Concise, professional, markdown-formatted

To modify the persona, edit `STUDIO_SYSTEM_PROMPT` in `graph.py`.

---

## LangGraph Flow

```
User message
     │
     ▼
preprocess_node  ←── entry point (future: guardrails, intent classification)
     │
     ▼
studio_agent_node
     │  calls SAP AI Core via sap_llm.py
     │  builds context: system prompt + full conversation history
     ▼
    END
```

The `@joule` routing happens in `app.py` before `graph.invoke()` is called — the graph itself always runs as the studio agent.

---

## Streamlit UI

To launch the full chat UI:

```bash
# From project root
streamlit run agent/eerly_studio/app.py
```

Open `http://localhost:8501` in your browser.

### @mention routing in the UI

| Input | Behaviour |
|---|---|
| `What is SAP BTP?` | Routed to Eerly Studio agent |
| `@joule What is S/4HANA?` | Routed to Joule agent via A2A bridge |

If Joule is offline (status = "offline" in `a2a_bridge.py`), the request falls back to Eerly Studio with a bridge note shown in the UI.

---

## Environment Variables

These are read from the `.env` file at project root:

| Variable | Required | Description |
|---|---|---|
| `AI_CORE_CLIENT_ID` | Yes | From AI Core service key → `uaa.clientid` |
| `AI_CORE_CLIENT_SECRET` | Yes | From AI Core service key → `uaa.clientsecret` |
| `AI_CORE_AUTH_URL` | Yes | Token URL → `uaa.url` + `/oauth/token` |
| `AI_CORE_API_URL` | Yes | AI API base URL → `serviceurls.AI_API_URL` |
| `AI_CORE_RESOURCE_GROUP` | No | Defaults to `default` |
| `SAP_MODEL_NAME` | No | Defaults to `gpt-4.1` |

---

## How sap_llm.py Works

`SAPChatOpenAI` is a LangChain-compatible wrapper that:

1. Fetches an OAuth2 token from `AI_CORE_AUTH_URL` using client credentials
2. Scans all running deployments via `GET /v2/lm/deployments`
3. Finds the deployment matching `SAP_MODEL_NAME` (e.g. `gpt-4.1`)
4. Initialises `ChatOpenAI` pointed at that deployment's URL
5. Adds the `AI-Resource-Group` header to every request

This means you never need to hardcode a deployment ID — it is discovered automatically.

---

## Replacing This Module With Real Eerly AI Studio

When Accely provides the real Eerly AI Studio API:

**Step 1** — Update `.env` at project root:

```dotenv
AGENT_PROVIDER=eerly
AGENT_BASE_URL=https://api.eerly.ai          # real Eerly base URL
AGENT_API_KEY=your-eerly-api-key
```

**Step 2** — Confirm the response field name with Accely and update `bridge/adapter.py` if needed.

**Step 3** — Run validation:

```bash
python bridge/test_adapter.py
python tests/test_e2e.py
```

This module (`agent/eerly_studio/`) can remain in the repo as a reference implementation and fallback. No other code changes are needed.

---

## Troubleshooting

### `ValueError: SAP AI Core credentials missing`

The `.env` file is not being loaded from the right path. Confirm you are running uvicorn from the project root, not from inside `agent/eerly_studio/`.

```bash
# Correct
cd sap-btp-a2a
uvicorn agent.eerly_studio.api:app --port 8000 --reload

# Wrong — will fail
cd agent/eerly_studio
uvicorn api:app --port 8000 --reload
```

### `RuntimeError: No RUNNING deployment found for model 'gpt-4.1'`

The `sap_llm.py` auto-discovery found no running deployment matching the model name. Go to SAP AI Launchpad → ML Operations → Deployments and confirm a deployment is in **Running** status. If the model name differs, update `SAP_MODEL_NAME` in `.env`.

### Port 8000 already in use

```bash
# Windows — find and kill the process
netstat -ano | findstr :8000
taskkill /PID <pid> /F
```